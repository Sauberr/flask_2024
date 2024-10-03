import pprint
import random
import datetime
import pandas as pd
import csv
import bcrypt
from http import HTTPStatus
import requests
import httpx

from string import ascii_lowercase, ascii_uppercase, digits, punctuation

from faker import Faker
from flask import Flask, request, jsonify, Response

from webargs import fields, validate
from webargs.flaskparser import use_args, use_kwargs

from database_handler import execute_query
from helpers import format_records

app = Flask(__name__)


@app.route('/')
def hello_world() -> str:
    return '<p>Hello, World!</p>'


@app.route('/hello')
def hello_dima() -> str:
    return '<p>Hello, Dima!</p>'


@app.route('/now')
def get_datetime() -> str:
    return f'Current time: {datetime.datetime.now()}'


@app.route('/password-generator')
def password_generator() -> str:
    """
    from 10 to 20 chars
    upper,lower case and special symbols
    """

    password_length = random.randint(10, 20)
    available_characters = (ascii_lowercase, ascii_uppercase, digits, punctuation)
    password = "".join([random.choice(available) for available in available_characters])
    password += "".join(random.choices(random.choice(available_characters),
                                       k=password_length - len(available_characters)))
    return f"Generated password: {password}"


@app.route('/average-statistics')
def calculate_average(filename: str = 'hw.csv') -> str:
    """
    csv file with students
    1.calculate average high
    2.calculate average weight
    csv - use lib
    *pandas - use pandas for calculating
    """

    df = pd.read_csv(filename)

    average_height = df[' Height(Inches)'].mean()
    average_weight = df[' Weight(Pounds)'].mean()

    return f"Average height: {round(average_height, 2)}, Average weight: {round(average_weight, 2)}"


@app.route('/get-password_generator')
@use_kwargs(
    {
        'length': fields.Int(
            required=True,
            validate=[validate.Range(min=8, max=100)]
        )
    },
    location='query'
)
def get_password_generator(length: int) -> str:

    return "".join(random.choices(
        ascii_lowercase + ascii_uppercase + digits, k=length
    ))


@app.route('/generate-students')
@use_kwargs(
    {
        'count': fields.Int(
            missing=5,
            validate=[validate.Range(min=1, max=1000)]
        )
    },
    location='query'
)
def generate_students(count: int):

    faker = Faker('UK')

    students_info = list()

    password = faker.password().encode('utf-8')
    salt = bcrypt.gensalt()

    for _ in range(count):
        first_name = faker.first_name()
        last_name = faker.last_name()
        email = faker.email()
        hashed_password = bcrypt.hashpw(password, salt)
        birthday = faker.date_of_birth()
        students_info.append([first_name, last_name, email, hashed_password, birthday])
    with open('students.csv', 'w', encoding='utf-8', newline='') as csvfile:
        fieldnames = ['first_name', 'last_name', 'email', 'password', 'birthday']
        writer = csv.DictWriter(csvfile, dialect='excel', fieldnames=fieldnames)
        writer.writeheader()
        for student in students_info:
            writer.writerow(
                {
                    'first_name': student[0],
                    'last_name': student[1],
                    'email': student[2],
                    'password': student[3],
                    'birthday': student[4]
                }
            )

    return (f'<p>First name: {student[0]}, Last name: {student[1]}, Email: {student[2]}, ' \
              f'Password {student[3]}, Birthday {student[4]}</p> <br>' for student in students_info)


@app.route('/bitcoin-rate')
@use_kwargs({
    'currency': fields.Str(
        load_default='USD',
        ),
    },
    location='query'
)
def get_bitcoin_value(currency: str) -> str:
    rates_url = f'https://bitpay.com/api/rates/{currency}'
    rates_result = requests.get(rates_url, {})
    if rates_result.status_code not in (HTTPStatus.OK, ):
        return Response(
            'ERROR: Something went wrong.',
            status=rates_result.status_code,
        )
    rates_result = rates_result.json()
    currencies_url = 'https://bitpay.com/currencies'
    currencies_result = requests.get(currencies_url, {})
    if currencies_result.status_code not in (HTTPStatus.OK, ):
        return Response(
            'ERROR: Something went wrong.',
            status=currencies_result.status_code,
        )
    currencies_result = currencies_result.json()
    rate = rates_result.get('rate', '?')
    symbol = currency
    for entry in currencies_result.get('data', {}):
        if currency == entry.get('code', {}):
            symbol = entry.get('symbol', currency)
            break
    return f'The bitcoin rate is {rate} {symbol}'


@app.route('/get-astronauts')
def get_astronauts():
    url = 'http://api.open-notify.org/astros.json'
    result = httpx.get(url)

    if result.status_code not in (HTTPStatus.OK, ):
        return Response(
            'ERROR: Something went wrong.',
            status=result.status_code,
        )

    result = result.json()
    pprint.pprint(result)

    statistics = {}

    for entry in result.get('people', {}):
        statistics[entry['craft']] = statistics.get(entry['craft'], 0) + 1

    return statistics


@app.route('/get-customers')
@use_kwargs(
    {
        'first_name': fields.Str(
            load_default=None,
            validate=[validate.Regexp('[a-zA-Z]+')]
        ),
        'last_name': fields.Str(
            load_default=None,
        ),
    },
    location='query'
)
def get_customers(first_name: str, last_name: str):
    query = 'SELECT * FROM customers'
    _fields = {}

    if first_name:
        _fields['FirstName'] = first_name
    if last_name:
        _fields['LastName'] = last_name

    if _fields:
        query += " WHERE " + " AND ".join(f"{key}=?" for key in _fields.keys())

    # pprint.pprint(query)

    records = execute_query(query, args=(_fields.values()))

    # pprint.pprint(records)
    return format_records(records)


@app.route('/stats-by-city')
@use_kwargs(
    {
        'genre': fields.Str(
            required=True,
            validate=[validate.Regexp('[a-zA-Z]+'), validate.Length(min=3)],
        ),
    },
    location='query'
)
def get_city_by_most_popular_genre(genre: str) -> str:
    query = f"SELECT BillingCity FROM (SELECT genres.Name as Genres, invoices.BillingCity, COUNT(invoices.BillingCity)" \
            f" FROM genres JOIN tracks ON genres.GenreId = tracks.GenreId JOIN invoice_items ON" \
            f" tracks.TrackId = invoice_items.TrackId JOIN invoices ON invoice_items.InvoiceId = invoices.InvoiceId" \
            f" Where Genres = \"{genre}\")";

    records = execute_query(query)

    if records == [(None, None, 0)]:
        return "ERROR: No such genre found"


    return format_records(*records)


@app.route('/get-all-info-about-track')
@use_kwargs(
    {
        "track_id": fields.Int(
            load_default=1,
            validate=[validate.Range(min=1)]
        ),
    },
    location='query'
)
def get_all_info_about_track(track_id: int) -> str:

    query = f"SELECT tracks.TrackId, tracks.Name AS Track, tracks.Composer, albums.Title AS Album," \
            f" artists.ArtistId, artists.Name AS Artist, genres.Name AS Genre, playlists.Name AS Playlist," \
            f" tracks.Bytes AS Size FROM tracks JOIN albums ON tracks.AlbumId = albums.AlbumId = albums.AlbumId JOIN" \
            f" artists ON albums.ArtistId = artists.ArtistId JOIN genres ON tracks.GenreId = genres.GenreId JOIN " \
            f"playlist_track ON tracks.TrackId = playlist_track.TrackId JOIN " \
            f"playlists ON playlist_track.PlaylistId = playlists.PlaylistId WHERE tracks.TrackId = {track_id}" \
            f" GROUP BY tracks.TrackId"

    records = execute_query(query)

    return format_records(records)


@app.route('/get-all-info-about-track-and-albums-in-hours')
@use_kwargs(
    {
        "track_id": fields.Int(
            load_default=1,
            validate=[validate.Range(min=1)]
        ),
    },
    location='query'
)
def get_all_info_about_track_and_albums_in_hours(track_id: int) -> str:

    query = f"SELECT tracks.TrackId, tracks.Name AS Track, tracks.Composer, albums.Title AS Album," \
            f" artists.Name AS Artist, genres.Name AS Genre, playlists.Name AS Playlist," \
            f" floor((tracks.Milliseconds / (1000 * 60)) % 60) || 'm:' || floor((tracks.Milliseconds / 1000) % 60)" \
            f" || 's' AS Time, tracks.Bytes AS Size FROM tracks JOIN albums ON tracks.AlbumId = albums.AlbumId JOIN" \
            f" artists on albums.ArtistId = artists.ArtistId JOIN genres ON tracks.GenreId = genres.GenreId JOIN" \
            f" playlist_track ON tracks.TrackId = playlist_track.TrackId JOIN " \
            f" playlists ON playlist_track.PlaylistId = playlists.PlaylistId WHERE tracks.TrackId = {track_id}" \
            f" GROUP BY tracks.TrackId"

    records = execute_query(query)

    return format_records(records)


@app.route('/sales')
@use_kwargs(
    {
        "country": fields.Str(
            load_default="",
            validate=[validate.Regexp('[a-zA-Z]+')]
        ),
    },
    location='query'
)
def order_price(country: str) -> str:
    if country:
        filter_query = f' WHERE BillingCountry = "{country}"'
        query = f" SELECT SUM(UnitPrice * Quantity) AS Sales, BillingCountry FROM invoice_items" \
                 f" JOIN invoices ON invoices.InvoiceId = invoice_items.InvoiceId {filter_query}" \
                 f" GROUP BY BillingCountry"
    else:
        query = f" SELECT SUM(UnitPrice * Quantity) AS Sales, BillingCountry FROM invoice_items" \
                 f" JOIN invoices ON invoices.InvoiceId = invoice_items.InvoiceId GROUP BY BillingCountry" \

    records = execute_query(query)
    return format_records(records)

if __name__ == '__main__':
    app.run(port=5001, debug=True)
