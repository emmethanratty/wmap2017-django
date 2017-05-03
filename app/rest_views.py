import json
from . import serializers
import urllib
from django.contrib.auth import authenticate, login
from rest_framework import permissions, authentication, status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import exceptions
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from app.models import *


class UsersList(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = serializers.UserOtherSerializer

    def get_queryset(self):
        return get_user_model().objects.all().order_by("username")

    def get_serializer_context(self):
        return {"request": self.request}


class UserMe_R(generics.RetrieveAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = serializers.UserMeSerializer

    def get_object(self):
        return get_user_model().objects.get(email=self.request.user.email)


class UserOther_R(generics.RetrieveAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        if "uid" in self.kwargs and self.kwargs["uid"]:
            users = get_user_model().objects.filter(id=self.kwargs["uid"])
        elif "email" in self.kwargs and self.kwargs["email"]:
            users = get_user_model().objects.filter(email=self.kwargs["email"])
        else:
            users = None
        if not users:
            self.other = None
            raise exceptions.NotFound
        self.other = users[0]
        return self.other

    def get_serializer_class(self):
        if self.request.user == self.other:
            return serializers.UserMeSerializer
        else:
            return serializers.UserOtherSerializer


class UpdatePosition(generics.UpdateAPIView):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = serializers.UserMeSerializer

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(UpdatePosition, self).dispatch(*args, **kwargs)

    def get_object(self):
        return get_user_model().objects.get(email=self.request.user.email)

    def perform_update(self, serializer, **kwargs):
        try:
            lat1 = float(self.request.data.get("lat", False))
            lon1 = float(self.request.data.get("lon", False))
            # lat2 = float(self.request.query_params.get("lat", False))
            # lon2 = float(self.request.query_params.get("lon", False))
            if lat1 and lon1:
                point = Point(lon1, lat1)
            # elif lat2 and lon2:
            #     point = Point(lon2, lat2)
            else:
                point = None

            if point:
                # serializer.instance.last_location = point
                serializer.save(last_location = point)
            return serializer
        except:
            pass


@api_view(["GET", ])
@permission_classes((permissions.AllowAny,))
# @csrf_exempt
def token_login(request):
    if (not request.GET["username"]) or (not request.GET["password"]):
        return Response({"detail": "Missing username and/or password"}, status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(username=request.GET["username"], password=request.GET["password"])
    if user:
        if user.is_active:
            login(request, user)
            try:
                my_token = Token.objects.get(user=user)
                return Response({"token": "{}".format(my_token.key)}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"detail": "Could not get token"})
        else:
            return Response({"detail": "Inactive account"}, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response({"detail": "Invalid User Id of Password"}, status=status.HTTP_400_BAD_REQUEST)


# function to load the walks API and input to the database, also return the data from the database to the frontend
@api_view(['GET', ])
@permission_classes((permissions.AllowAny,))
def walks(request):
    print('in walks')

    # try catch block in case the API page is down
    try:
        # get the API data
        walks_file = urllib.urlopen('https://data.dublinked.ie/dataset/b1a0ce0a-bfd4-4d0b-b787-69a519c61672/resource/b38c4d25-097b-4a8f-b9be-cf6ab5b3e704/download/walk-dublin-poi-details-sample-datap20130415-1449.json')
        walks_string = walks_file.read()
        walks_file.close()
        walks_json = json.loads(walks_string)

        # insert the data to the database
        for walk in walks_json:

            walks_db = WalksDB(id=walk["poiID"], name=walk["name"], latitude=walk["latitude"], longitude=walk["longitude"],
                               address=walk["address"], description=walk["description"], contactNumber=walk["contactNumber"]
                               , imageFileName=walk["imageFileName"])
            walks_db.save()

    except Exception as e:
        print("Dub linked API Error")

    # selects all ratings from the database
    all_ratings = RatingDB.objects.all()

    ratings_array = []
    first_rating = all_ratings.first()
    walks_id = first_rating.walk_id
    count = 0
    total = 0

    # loop to get the average for each walk
    for single_rating in all_ratings:
        # when the id changes the average is appended to an array
        if walks_id != single_rating.walk_id:

            average = total/count
            ratings = [walks_id, "{0:.2f}".format(average)]

            ratings_array.append(ratings)
            count = 0
            total = 0
            walks_id = single_rating.walk_id

        total += float(single_rating.rating)
        count += 1

    ratings = [walks_id, "{0:.2f}".format(total/count)]

    ratings_array.append(ratings)
    r = []

    # for loop to create the objects, to pass back to the frontend
    for rate in ratings_array:
        r.append({
            'id': str((rate[0])),
            'average': str((rate[1])),
        })

    # making the rating object list into JSON
    rating_json = json.dumps(r)

    # get all the walks information from the database
    all_walks = WalksDB.objects.all()

    w = []
    # loop to create the object data for walks, to pass to frontend
    for walk in all_walks:
        w.append({
            'poiID': str(walk.id),
            'name': walk.name,
            'latitude': str(walk.latitude),
            'longitude': str(walk.longitude),
            'address': walk.address,
            'description': walk.description,
            'contactNumber': str(walk.contactNumber),
            'imageFileName': str(walk.imageFileName),
        })

    # change the objects into JSON
    walks_final_json = json.dumps(w)
    print(walks_final_json)

    return Response({"data": walks_final_json, "rating": rating_json}, status=status.HTTP_200_OK)


# function to insert the ratings into the RatingDB
@api_view(['GET', ])
@permission_classes((permissions.AllowAny,))
def rating(request):
    print('in rating')

    rating_db = RatingDB(username=request.GET.get('rating_username'), walk_id=int(request.GET.get('rating_id')),
                         rating=int(request.GET.get('rating')))

    rating_db.save()

    print(request.GET.get('rating_id'))
    print(request.GET.get('rating'))
    return Response({}, status=status.HTTP_200_OK)


# function to return all the rating data to the front end
@api_view(['GET', ])
@permission_classes((permissions.AllowAny,))
def listreviews(request):

    # get all the rating data from the database
    all_ratings = RatingDB.objects.filter(walk_id=request.GET.get('walk_id'))
    r = []

    # loop to convert data into objects
    for rate in all_ratings:
        r.append({
            'id': rate.walk_id,
            'username': rate.username,
            'rating': rate.rating,
        })

    # change the objects into JSON to pass to frontend
    rating_json = json.dumps(r)

    return Response({'rating_list': rating_json}, status=status.HTTP_200_OK)


# function to register a user into the database
@api_view(['GET', ])
@permission_classes((permissions.AllowAny,))
@csrf_exempt
def registration(request):

    # get all information from the request
    username = request.GET.get('username')
    first_name = request.GET.get('first_name')
    last_name = request.GET.get('last_name')
    email = request.GET.get('email')
    password = request.GET.get('password')

    # try to check if user is in the database already
    try:
        user = get_user_model().objects.get(username=username)
        if user:
            return Response({}, status=status.HTTP_400_BAD_REQUEST)
    except get_user_model().DoesNotExist:

        # create and insert the new user model
        user = get_user_model().objects.create_user(username=username)
        # Set user fields provided
        user.set_password(password)
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()
        return Response({}, status=status.HTTP_200_OK)

    return Response({}, status=status.HTTP_400_BAD_REQUEST)
