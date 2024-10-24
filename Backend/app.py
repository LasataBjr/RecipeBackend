from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime

app = Flask(__name__)
CORS(app) #enable cors for all the routes

#connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['login'] #for login page
users_collection = db['login_people']

db1 = client['Food']#for food page

#Recipe insert route
@app.route('/addRecipe', methods= ['POST'])
def addRecipe():
    data = request.json
    category = data.get('category') #Chicken, Buffalo, Pig, Fish, Bakery
    title = data.get('title') #Chicken Curry,....
    image = data.get('image', None) 
    ingredients = data.get('ingredients', [])
    steps = data.get('steps', [])
    likes = data.get('likes', 0)
     
    #right collection to be selected
    collection = f"{category.lower()}_recipe"
    foodtype = db1[collection]

    recipe = {
        "title": title,
        "image": image,
        "likes": likes,
        "date": datetime.utcnow(),
        "ingredients": ingredients,
        "steps": steps
    }

    foodtype.insert_one(recipe)
    #always give in alert form
    return jsonify ({'message':f'Recipe added to {category} category'}),201

#Route To all recepies fetch(display)
@app.route('/get_recipes', methods=['GET']) 
def get_recipes():
    category = request.args.get('category', None) #  fetches the value of a query parameter from the URL, specifically the category parameter, none for fetching all data if category have no value

    if category: #If a category is specified, this block of code runs
        collection = f"{category.lower()}_recipe"
        foodtype = db1[collection] #finding collection from the db
        recipes = list(foodtype.find())
    else:
        collections = ['chicken_recipe','buff_recipe','port_recipe','veg_recipe','fish_recipe','bakery_recipe']
        recipes = []
        for col in collections:
            foodtype = db1[col]
            recipes += list(foodtype.find())

    for recipe in recipes:
        recipe['_id'] = str(recipe['_id'])

    return jsonify(recipes),200 #Converts the recipes list into JSON format.

#Delete route
@app.route('/del_recipes<string:id>', methods =['DELETE'])
def del_recipe(id):
    category = request.args.get('category')

    if not category:
        return jsonify({'file not found'}),400
    
    collection = f"{category.lower()}_recipe"
    foodtype = db1[collection]

    result = foodtype.delete_one({'_id': ObjectId(id)})

    if result.deleted_count == 1:
        return jsonify({'recipe deleted'}),200
    else:
        return jsonify({'result not found'}),400
    
#Signup ROute
@app.route('/signup', methods = ['POST'])
def signup():
    username = request.json.get('username')
    password = request.json.get('password')
    hashed_password = generate_password_hash(password)
    
    users_collection.insert_one({'username':username, 'password':hashed_password})

    return jsonify({'message': 'Signup Succesful'}), 201



#LOGIN ROUTE
@app.route('/login', methods=['POST'])
def login():
        username = request.json.get('username')
        password = request.json.get('password')

        user = users_collection.find_one({'username': username})

        if user and check_password_hash(user['password'],password):
            return jsonify({'message': 'Login Succesful'}), 200
        else:
            return jsonify({'message': 'invalid input'}), 401

if __name__ == '__main__':
    app.run(debug=True)
