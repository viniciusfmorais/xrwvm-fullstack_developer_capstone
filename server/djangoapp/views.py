# Uncomment the required imports before adding the code

# from django.shortcuts import render
# from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.models import User
# from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import logout
# from django.contrib import messages
# from datetime import datetime
from .models import CarMake, CarModel
from .restapis import get_request, analyze_review_sentiments, post_review, searchcars_request
from django.http import JsonResponse
from django.contrib.auth import login, authenticate
import logging
import json
from django.views.decorators.csrf import csrf_exempt
from .populate import initiate

# Get an instance of a logger
logger = logging.getLogger(__name__)
# Create your views here.
# Create a `login_request` view to handle sign in request
@csrf_exempt
def login_user(request):
    data = json.loads(request.body)
    username = data["userName"]
    password = data["password"]
    user = authenticate(username=username, password=password)
    data = {"userName": username}
    if user is not None:
        login(request, user)
        data = {"userName": username, "status": "Authenticated"}
    return JsonResponse(data)

# Create a `logout_request` view to handle sign out request
def logout_request(request):
    logout(request)
    data = {"userName": ""}
    return JsonResponse(data)

# Create a `registration` view to handle sign up request
@csrf_exempt
def registration(request):
    data = json.loads(request.body)
    username = data["userName"]
    password = data["password"]
    first_name = data["firstName"]
    last_name = data["lastName"]
    email = data["email"]
    if User.objects.filter(username=username).exists():
        return JsonResponse({"status": "User already exists"})

    user = User.objects.create_user(
        username=username,
        first_name=first_name,
        last_name=last_name,
        password=password,
        email=email,
    )

    login(request, user)
    data = {"userName": username, "status": "Authenticated"}
    return JsonResponse(data)

def get_cars(request):
    count = CarMake.objects.filter().count()
    print(count)
    if count == 0:
        initiate()
    car_models = CarModel.objects.select_related("car_make")
    cars = []
    for car_model in car_models:
        cars.append({
            "CarModel": car_model.name,
            "CarMake": car_model.car_make.name
        })
    return JsonResponse({"CarModels": cars})

def get_dealerships(request, state="All"):
    if state == "All":
        endpoint = "/fetchDealers"
    else:
        endpoint = "/fetchDealers/" + state
    dealerships = get_request(endpoint)
    return JsonResponse({"status": 200, "dealers": dealerships})

def get_dealer_reviews(request, dealer_id):
    if dealer_id:
        endpoint = "/fetchReviews/dealer/" + str(dealer_id)
        reviews = get_request(endpoint)
        for review_detail in reviews:
            try:
                response = analyze_review_sentiments(
                    review_detail["review"]
                )
                if response:
                    print(response)
                    review_detail["sentiment"] = response.get(
                        "sentiment", "Unknown"
                    )
                else:
                    review_detail["sentiment"] = "Unknown"
            except Exception as e:
                print(f"Error analyzing sentiment: {e}")
                review_detail["sentiment"] = "Unknown"
        return JsonResponse({"status": 200, "reviews": reviews})
    else:
        return JsonResponse({"status": 400, "message": "Bad Request"})

def get_dealer_details(request, dealer_id):
    if dealer_id:
        endpoint = "/fetchDealer/" + str(dealer_id)
        dealership = get_request(endpoint)
        return JsonResponse({"status": 200, "dealer": dealership})
    else:
        return JsonResponse({"status": 400, "message": "Bad Request"})

def add_review(request):
    if request.user.is_anonymous is False:
        data = json.loads(request.body)
        try:
            post_review(data)
            return JsonResponse({
                "status": 200,
                "message": "Review posted successfully"
            })
        except Exception as err:
            return JsonResponse({
                "status": 401,
                "message": "Error in posting review: " + str(err)
            })
    else:
        return JsonResponse({
            "status": 403,
            "message": "Unauthorized"
        })

def get_inventory(request, dealer_id):
    data = request.GET
    if dealer_id:
        if 'year' in data:
            endpoint = "/carsbyyear/" + str(dealer_id) + "/" + data['year']
        elif 'make' in data:
            endpoint = "/carsbymake/" + str(dealer_id) + "/" + data['make']
        elif 'model' in data:
            endpoint = "/carsbymodel/" + str(dealer_id) + "/" + data['model']
        elif 'mileage' in data:
            endpoint = "/carsbymaxmileage/" + str(dealer_id) + "/" + data['mileage']
        elif 'price' in data:
            endpoint = "/carsbyprice/" + str(dealer_id) + "/" + data['price']
        else:
            endpoint = "/cars/" + str(dealer_id)

        cars = searchcars_request(endpoint)
        return JsonResponse({"status": 200, "cars": cars})
    else:
        return JsonResponse({"status": 400, "message": "Bad Request"})
