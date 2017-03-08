import re
import copy
import warnings

import requests

try:
    from lxml import html
except ImportError as e:
    warnings.warn(
        "lxml could not be imported. Automatic apikey retrieval will be unavailiable:\n{}".format(e)
        )

from pygflib.models import Question, Answer, Comment, User, QuestionStream, TagStream, AnswerStream


class InvalidResponseError(Exception):
    pass


class Gfapi():

    BASE_URL = "https://api.gutefrage.net"

    POST = "post"
    GET = "get"

    QUESTIONS = 'questions'
    USERS = 'users'
    COMMENTS = 'comments'
    ANSWERS = 'answers'
    TAGS = 'tags'

    LATEST = 'latest'
    SEARCH = 'search'

    SLUG = 'slug:'
    EMAIL = 'email:'

    DEFAULTHEADER = {
        'User-Agent' : 'Dalvik/2.1.0 (Linux; U; Android 7.1; Android SDK built for x86 Build/NPF26K)',
        'Accept' : 'application/json',
        'Accept-Language' : 'de,en-US;q=0.7,en;q=0.3',
        'DNT' : '1',
        'Connection' : 'close',
        'host' : 'api.gutefrage.net',
        'x-client-id' : 'net.gutefrage.mobile.android.phone.1.10.0.1384',
        'X-Api-Version' : '1',
        'X-WITH-FIELDS' : '1'
        }

    APIKEYHEADER = {
        'User-Agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:39.0) Gecko/20100101 Firefox/39.0',
        'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language' : 'de,en-US;q=0.7,en;q=0.3',
        'DNT' : '1',
        'referer' : 'http://www.gutefrage.net',
        'Connection' : 'keep-alive',
        'Origin' : 'http://www.gutefrage.net',
        }


    def __init__(self, apikey=None):

        if apikey is None:
            apikey = self.get_apikey()
        else:
            self.header = copy.deepcopy(self.DEFAULTHEADER)

        self.apikey = apikey
        self.header['X-Api-Key'] = apikey


    def get_apikey(self, header=None):
        self.header = copy.deepcopy(self.DEFAULTHEADER)

        if header is None:
            header = self.APIKEYHEADER

        response = requests.get('http://www.gutefrage.net/frage_hinzufuegen', headers=header)
        self.apikey = re.search(
            "key: '([^']+)'",
            html.document_fromstring(response.text).xpath('//script[1]')[0].text
            ).group(1)

        return self.apikey


    #TODO: improve this method to work better with tag queries
    def _apicall(self, objecttype, identifier='', fields=None, **kwargs):

        params = ''
        if kwargs:
            params = '&'.join(['{}={}'.format(param, value) for param, value in kwargs.items()])

        apiurl = '{}/{}{}{}{}{}{}{}'.format(
            self.BASE_URL,
            objecttype,
            '/' if identifier else '',
            identifier,
            "?" if fields is not None or params in kwargs else '',
            "fields={}".format(fields) if fields is not None else '',
            "&" if fields is not None else '',
            params
            )

        return self.get_gfurl(apiurl, fields)


    def get_gfurl(self, apiurl, fields='', mode=GET, json_payload=None):

        response = None
        if mode == self.GET:
            response = requests.get(apiurl, params={'fields' : fields}, headers=self.header)
        elif mode == self.POST:
            response = requests.post(apiurl, json=json_payload, headers=self.header)
        else:
            raise ValueError(mode + " is not a valid mode! Must be 'get' or 'post'")

        try:
            json = response.json()

        except ValueError:
            raise InvalidResponseError(
                "No json could be decoded from request: Status {}".format(response.status_code)
                )

        if "error" in json:
            raise InvalidResponseError(
                "api error excepted: {e[type]} - {e[message]}".format(e=json["error"])
                )

        if "message" in json:
            raise InvalidResponseError(
                "api error message excepted: {}".format(json["message"])
                )

        return json


    def login(self, username, password):

        response = self.get_gfurl(
            self.BASE_URL + "/access_tokens",
            mode=self.POST,
            json_payload={"username" : username, "password" : password}
            )

        self.header["Authorization"] = response["access_token"]

        return response["refresh_token"]


    def refresh(self, refresh_token):

        if "Authorization" in self.header:
            del self.header["Authorization"]

        response = self.get_gfurl(
            self.BASE_URL + "/access_tokens/refresh",
            mode=self.POST,
            json_payload={"refresh_token" : refresh_token}
            )

        self.header["Authorization"] = response["access_token"]

        return response["refresh_token"]


    def get_next_page(self, stream, fields=''):
        return self._get_type_stream(stream.TYPE, self.get_gfurl(stream.next(), fields))


    def get_previous_page(self, stream, fields=''):
        return self._get_type_stream(stream.TYPE, self.get_gfurl(stream.previous(), fields))


    def _get_type_stream(self, objecttype, json_item):
        if objecttype == self.ANSWERS:
            return AnswerStream(json_item)
        elif objecttype == self.QUESTIONS:
            return QuestionStream(json_item)
        elif objecttype == self.TAGS:
            return TagStream(json_item)


    def search_tags(self, query, fields='', limit=10):
        return TagStream(
            self._apicall(self.TAGS, fields=fields, prefix=query, limit=limit)
            )


    def get_recent_questions(self, fields='', limit=10):
        return QuestionStream(
            self._apicall(self.QUESTIONS, self.LATEST, fields, limit=limit)
            )


    def search_questions(self, query, fields='', limit=10):
        return QuestionStream(
            self._apicall(self.QUESTIONS, self.SEARCH, fields, limit=limit, query=query)
            )


    def get_question(self, identifier, fields='', id_type=None):
        return Question(
            self._apicall(
                self.QUESTIONS,
                id_type + identifier if id_type is not None else identifier,
                fields
                )
            )


    def get_question_answers(self, identifier, fields=''):
        json_item = self._apicall(self.QUESTIONS, u'{}/{}'.format(identifier, self.ANSWERS), fields)
        return [Answer(i) for i in json_item["items"]]


    def get_user(self, identifier, fields='', id_type=None):
        return User(
            self._apicall(
                self.USERS,
                id_type + identifier if id_type is not None else identifier,
                fields
                )
            )


    def get_answer(self, identifier, fields=''):
        return Answer(
            self._apicall(self.ANSWERS, identifier, fields)
            )


    def get_comment(self, identifier, fields=''):
        return Comment(
            self._apicall(self.COMMENTS, identifier, fields)
            )


    def get_user_questions(self, identifier, fields=''):
        return QuestionStream(
            self._apicall(self.USERS, u'{}/{}'.format(identifier, self.QUESTIONS), fields)
            )


    def get_user_answers(self, identifier, fields='', limit=20, mosthelpful=False, id_type=None):
        if mosthelpful:
            json_item = self._apicall(
                self.USERS,
                u'{}/{}'.format(
                    id_type + identifier if id_type is not None else identifier, self.ANSWERS
                    ),
                fields, onlyMostHelpful='True', limit=limit
                )

        json_item = self._apicall(
            self.USERS,
            u'{}/{}'.format(id_type + identifier if id_type is not None else identifier, self.ANSWERS),
            fields, limit=limit
            )

        return AnswerStream(json_item)
