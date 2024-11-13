import os
import json
import jwt
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from bson import ObjectId, errors
from pymongo import errors
from pymongo import DESCENDING
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app) #enable cors for all the routes


app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'
app.config['JWT_TOKEN_LOCATION'] = ['headers']

JWT = JWTManager(app)


if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

#connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['login'] #for login page
users_collection = db['login_people']
db1 = client['Food']#for food page

# Serve static files from 'uploads' folder
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

#LOGIN ROUTE
@app.route('/login', methods=['POST'])
def login():
        username = request.json.get('username')
        password = request.json.get('password')
        user = users_collection.find_one({'username': username})

        if user and check_password_hash(user['password'],password):
            token = jwt.encode({'user_id': str(user['_id']),'exp': datetime.utcnow() + timedelta(hours=2)},
            app.config['JWT_SECRET_KEY'], algorithm='HS256')

            return jsonify({'message': 'Login Succesful', 'token': token}), 200
        else:
            return jsonify({'message': 'invalid input'}), 401
        
#Signup ROute
@app.route('/signup', methods = ['POST'])
def signup():
    username = request.json.get('username')
    password = request.json.get('password')

    if not username or not password:
        return jsonify({'message':'Username and password are required'}),400
    
    if users_collection.find_one({'username': username}):
        return jsonify({'message': 'Username already exists'}),409

    hashed_password = generate_password_hash(password)
    
    try:
        users_collection.insert_one({'username':username, 'password':hashed_password})
        return jsonify({'message': 'Signup Successful'}),201
    except Exception as e:
        return jsonify({'message': f'An error occurred: {str(e)}'}),500
    
#SearchBar recipe fetch
@app.route('/recipePage/<id>', methods = ['GET'])
def recipePage(id):
    try:
        print(f"Fetching recipe with ID: {id}")
        categories = ['chicken_recipe', 'buff_recipe', 'pork_recipe', 'veg_recipe', 'fish_recipe', 'bakery_recipe']
        recipe = None

        for category in categories:
            collection = db1[category]
            recipe = collection.find_one({'_id': ObjectId(id)})
            if recipe:
                recipe['_id'] = str(recipe['_id'])
                print(f"Recipe found in {category}")
                break

        if recipe:
            return jsonify(recipe), 200
        else:
            print("recipe not found")
            return json({'message': 'Recipe not found'}),404
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'message': 'An error occured'}),500



#Recipe insert route
@app.route('/addRecipe', methods= ['POST'])
def addRecipe():
    # Use request.form instead of request.json for FormData
    category = request.form.get('category')  # Chicken, Buffalo, Pig, Fish, Bakery
    title = request.form.get('title')  # Chicken Curry, etc.
    image = request.files.get('image')
    ingredients = json.loads(request.form.get('ingredients'))
    steps = json.loads(request.form.get('steps'))
    
    likes = request.form.get('likes', 0)

    if not category or not title or not ingredients or not steps:
        return jsonify({'message': 'Missing required fields'}), 400

    image_url = None
    if image:
        filename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        image_url = f"http://localhost:5000/uploads/{filename}"

    # Right collection to be selected
    collection = f"{category.lower()}_recipe"
    foodtype = db1[collection]

    recipe = {
        "title": title,
        "image": image_url,
        "likes": int(likes),
        "liked_by": [],
        "date": datetime.utcnow(),
        "ingredients": ingredients,
        "steps": steps
    }

    foodtype.insert_one(recipe)
    return jsonify({'message': f'Recipe added to {category} category'}), 201

#Recipe edit route
@app.route('/recipeedit/<id>', methods= ['GET', 'PUT'])
@jwt_required()
def recipeedit(id):
    user_id = get_jwt_identity()
                # title = request.form.get('title')
                # ingredients = request.form.get('ingredients').split(', ')
                # steps = request.form.get('steps').split(', ')
                # image = request.form.get('image')

                # recipe = recipe.query.get(id)
                # if recipe:
                #     recipe.title = title
                #     recipe.ingredients = ingredients
                #     recipe.steps = steps
                #     if image:
                #         image_path = f"static/uploads/{image.filename}"
                #         image.save(image_path)
                #         recipe.image = image_path
                #     db.session.commit() 
                #     return jsonify({'Message' : 'Recipe Update Successfully'})
                # else:
                #     return jsonify({"Error" : "Recipe Not Updated"}), 404


    categories = ['chicken_recipe', 'buff_recipe', 'pork_recipe', 'veg_recipe', 'fish_recipe', 'bakery_recipe']
    
    # Ensure `id` is a valid ObjectId
    try:
        obj_id = ObjectId(id)
    except Exception:
        return jsonify({"message": "Invalid recipe ID"}), 400

    if request.method == 'GET':

            for category in categories:
                collection = db1[category]
                recipe = collection.find_one({'_id': obj_id})
                if recipe:
                    recipe['_id'] = str(recipe['_id'])
                    return jsonify(recipe), 200
            return jsonify({'message': 'Recipe not found'}), 404
        

    elif request.method == 'PUT':
        try:
            data = request.form
            title = data.get('title')
            ingredients = data.getlist('ingredients')
            steps = data.getlist('steps')

            for category in categories:
                collection = db1[category]
                recipe = collection.find_one({'_id': obj_id})
                if recipe:
                    update_data = {
                        'title': title,
                        'ingredients': ingredients,
                        'steps': steps
                    }

                    # Update the recipe in the database
                    collection.update_one(
                        {'_id': obj_id},
                        {'$set': update_data}
                    )
                    return jsonify({'message': 'Recipe updated successfully'}), 200

            return jsonify({'message': 'Recipe not found'}), 404
        except Exception as e:
            print(f"Error: {e}")
            return jsonify({"message": "An error occurred while updating the recipe"}), 500

#Route To all recepies fetch(display)
@app.route('/get_recipes', methods=['GET']) 
def get_recipes():
    category = request.args.get('category', None) #  fetches the value of a query parameter from the URL, specifically the category parameter, none for fetching all data if category have no value
    sort_by = request.args.get('sort', None)
    
    recipes = []

    if category: #If a category is specified, this block of code runs
        collection = f"{category.lower()}_recipe"
        foodtype = db1[collection] #finding collection from the db
        
        if sort_by == "popular":
            recipes = list(foodtype.find().sort("likes",-1).limit(3))
        else:
            recipes = list(foodtype.find().limit(3))

    else:
        collections = ['chicken_recipe','buff_recipe','pork_recipe','veg_recipe','fish_recipe','bakery_recipe']
        
        for col in collections:
            foodtype = db1[col]
            category_recipes = foodtype.find()

            if sort_by == 'popular':
                category_recipes = category_recipes.sort("likes",-1).limit(3)
            else:
                category_recipes = category_recipes.limit(3)
            
            recipes += list(category_recipes)

    for recipe in recipes:
        recipe['_id'] = str(recipe['_id'])

    return jsonify(recipes),200 #Converts the recipes list into JSON format.

#ROute to fetch the latest recipes
@app.route('/latest_recipes', methods=['GET'])
def get_latest_recipes():
    recipes = []
    categories = ['chicken_recipe', 'buff_recipe', 'pork_recipe', 'veg_recipe', 'fish_recipe', 'bakery_recipe']

    for category in categories:
        collection = db1[category]
        category_recipes = list(collection.find().sort("date" , DESCENDING).limit(3))

        for recipe in category_recipes:
            recipe['_id'] = str(recipe['_id'])
            recipe['category'] = category
            recipes.append(recipe)

    sorted_recipes =  sorted(recipes, key= lambda x : x.get('date', datetime.min), reverse = True)[:3]   
    return jsonify(sorted_recipes),200

#Search recipes Route
@app.route('/search_recipes', methods=['GET'])
def search_recipes():
    query = request.args.get('query', '').strip()#This method allows you to access values passed in the query string, which is the part of the URL that comes after the question mark (?).
    if not query:
        return jsonify({'message':'Query is required'}), 400

    categories = ['chicken_recipe', 'buff_recipe', 'pork_recipe', 'veg_recipe', 'bakery_recipe', 'fish_recipe']
    search_results = []

    for category in categories:
        collection = db1[category]

        category_recipes = list(collection.find({ 
                "title" : {"$regex" : query, "$options" : "i" }
        }))

        for recipe in category_recipes:
            recipe['_id'] = str(recipe['_id'])
            recipe['category'] = category
            search_results.append(recipe)

    return jsonify(search_results), 200

#fetch top 3 popular recipes
@app.route('/popular_recipes', methods=['GET'])
def get_popular_recipes():
    recipes = []
    categories = ['chicken_recipe', 'buff_recipe', 'pork_recipe', 'veg_recipe', 'fish_recipe', 'bakery_recipe']

    # Collect recipes from all categories
    for category in categories:
        collection = db1[category]
        category_recipes = list(collection.find())
        
        for recipe in category_recipes:
            recipe['_id'] = str(recipe['_id'])
            recipe['category'] = category
            recipes.append(recipe)

    # Sort recipes by likes and limit to top 3
    top_recipes = sorted(recipes, key=lambda x: x.get('likes', 0), reverse=True)[:3]

    return jsonify(top_recipes), 200

#toggle_like route
@app.route('/toggle_like/<id>', methods=['POST'])
@jwt_required()
def toggle_like(id):
    data = request.get_json()
    user_id = get_jwt_identity()

    collection = db1["recipes"]
    recipe = collection.find_one({'_id': ObjectId(id)})

    if recipe:
        if user_id in recipe.get('liked_by', []):
            new_likes = max(recipe.get('likes', 1) - 1, 0)
            collection.update_one(  
                {'_id': ObjectId(id)},
                {'$set': {'likes': new_likes}, '$pull': {'liked_by': user_id}}
            )
            return jsonify({'likes': new_likes, 'liked': False}), 200
        else:
            new_likes = recipe.get('likes', 0) + 1
            collection.update_one(
                {'_id': ObjectId(id)},
                {'$set': {'likes': new_likes}, '$addToSet': {'liked_by': user_id}}
            )
            return jsonify({'likes': new_likes, 'liked': True}), 200  

    return jsonify({'message': 'Recipe not found'}), 404



# #Unlike route
# @app.route('/unlike_recipe/<id>', methods=['POST'])
# def unlike_recipe(id):
#     data = request.get_json()
#     category = data.get('category')

#     if category:
#         collection = db1[category]
#         try: 
#             recipe = collection.find_one({'_id': ObjectId(id)})
#         except errors.InvalidId:
#             return jsonify({'message': 'Invalid recipe ID format'}),400

#         if recipe and recipe.get('likes', 0) > 0:
            
#             new_likes = recipe.get('likes', 0) - 1
#             collection.update_one({'_id': ObjectId(id)},{'$set':{'likes': new_likes}})
#             return jsonify({'message':'Like is decreased','likes': new_likes}),200
#     return jsonify({'message':'Dislike is unsuccessful'}),400

#Delete route
@app.route('/del_recipes/<id>', methods =['DELETE'])
def del_recipes(id):
    category = request.args.get('category')

    if not category:
        return jsonify({'message':'file not found'}),400
    
    collection = f"{category.lower()}_recipe"
    if collection not in db1.list_collection_names():
        return jsonify({'message': 'Category does not exist'}), 400

    try:
        object_id = ObjectId(id)
    except errors.InvalidId:
        return jsonify({'message': 'Invalid ID format'}), 400
   
    foodtype = db1[collection]
    recipe = foodtype.find_one({'_id':ObjectId(id)})
    if not recipe:
        return jsonify({'message':'Recipe not found'}),404
    
    if recipe.get('image'):
        filename = os.path.basename(recipe['image'])
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path): #to remove from the upload file where the image have been stored when added at db
            os.remove(file_path)
        
    
    result = foodtype.delete_one({'_id': ObjectId(id)})

    if result.deleted_count == 1:
        return jsonify({'message':'recipe deleted'}),200
    else:
        return jsonify({'message':'result not found'}),400
    


if __name__ == '__main__':
    app.run(debug=True)
