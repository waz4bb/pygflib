"""
The part of the api that handles recieving and sending data as well as authorization.
"""
import re
import copy
import warnings
import functools

import requests

try:
    from lxml import html
except ImportError as error:
    warnings.warn(
        "lxml could not be imported. Automatic apikey retrieval will be unavailiable:"
        + "\n{}".format(error)
        )

from pygflib.models import Question, Answer, Comment, User, QuestionStream, TagStream, AnswerStream


class UnauthorizedError(Exception):
    """Represents authorization failures and lack of authorization keys."""


class InvalidResponseError(Exception):
    """Represents connection issues and response errors from api calls."""


def authorized(wrapped):
    """
    A decorator that checks for authorization before calling the underlying function.

    :raise UnauthorizedError: Raised when the authentication key is missing
    """
    @functools.wraps(wrapped)
    def _auth_check(self, *args, **kwargs):
        if "Authorization" not in self.header:
            raise UnauthorizedError(
                "This action requires authorization. Use login or refresh first."
                )

        return wrapped(self, *args, **kwargs)

    return _auth_check


def special_apikey_required(wrapped):
    """A decorator that temporarily changes the apikey to a special key for a function."""
    @functools.wraps(wrapped)
    def _apikey_switch(self, *args, **kwargs):
        self.header['X-Api-Key'] = self.SPECIAL_APIKEY
        response = wrapped(self, *args, **kwargs)
        self.header['X-Api-Key'] = self.apikey
        return response

    return _apikey_switch


class Gfapi():
    """
    Handles API connections and keeps track of authorization.

    Most functions can be called without authorization and return the same results.

    :data SLUG: A flag for slug requests
    :data EMAIL: A flag for email requests. Only usable in :func:`user() <core.Gfapi.user>`.
    :data SPECIAL_APIKEY: The special api key used by functions decorated
       with :func:`@special_apikey_required <core.special_apikey_required>`

    :attribute apikey: The apikey used by this instance
    :attribute header: The current header used for api calls
    """

    SPECIAL_APIKEY = '003fd9bf-4150-4524-b3cb-8920b7cd807c'

    BASE_URL = 'https://api.gutefrage.net'

    _POST = 'post'
    _GET = 'get'

    _QUESTIONS = 'questions'
    _USERS = 'users'
    _COMMENTS = 'comments'
    _ANSWERS = 'answers'
    _TAGS = 'tags'

    _LATEST = 'latest'
    _SEARCH = 'search'

    SLUG = 'slug:'
    EMAIL = 'email:'

    DEFAULTHEADER = {
        'User-Agent' : 'Dalvik/2.1.0 (Linux; U; Android 7.1; Android SDK built for x86 Build/NPF26K)',
        'Accept' : 'application/json',
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
        """
        If ``apikey`` is not given, automatic retrieval of a key
        from `gutefrage.net <https://gutefrage.net>`_ is attempted.

        This key is used for all api calls except for functions
        decorated with :func:`@special_apikey_required <core.special_apikey_required>`.

        .. note::
           Automatic Link retrieval requires **lxml** to be :ref:`installed <installation>`

        :param apikey: The apikey used for most api calls
        """

        if apikey is None:
            apikey = self.get_apikey()
        else:
            self.apikey = apikey
            self.header = copy.deepcopy(self.DEFAULTHEADER)
            self.header['X-Api-Key'] = apikey


    def get_apikey(self, header=None):
        """
        Retrieve and sets a new apikey.

        :param header: a custom header for retrieving the apikey.
        """

        self.header = copy.deepcopy(self.DEFAULTHEADER)

        if header is None:
            header = self.APIKEYHEADER

        response = requests.get('http://www.gutefrage.net/frage_hinzufuegen', headers=header)
        self.apikey = re.search(
            "key: '([^']+)'",
            html.document_fromstring(response.text).xpath('//script[1]')[0].text
            ).group(1)

        self.header['X-Api-Key'] = self.apikey

        return self.apikey


    #TODO: rework this function eventually
    def _apicall(self, objecttype, identifier='', fields=None, **kwargs):

        params = ''
        if kwargs:
            params = '&'.join(['{}={}'.format(param, value) for param, value in kwargs.items()])

        apiurl = '{}/{}{}{}{}{}{}{}'.format(
            self.BASE_URL,
            objecttype,
            '/' if identifier else '',
            identifier,
            '?' if fields is not None or params in kwargs else '',
            params,
            '&' if params else '',
            'fields={}'.format(fields) if fields is not None else ''
            )

        return self._get_gfurl(apiurl, fields)


    def _get_gfurl(self, apiurl, fields='', mode=_GET, json_payload=None):

        response = None
        if mode == self._GET:
            response = requests.get(apiurl, params={'fields' : fields}, headers=self.header)
        elif mode == self._POST:
            response = requests.post(apiurl, json=json_payload, headers=self.header)
        else:
            raise ValueError(mode + " is not a valid mode! Must be 'get' or 'post'")

        try:
            json = response.json()

        except ValueError:
            raise InvalidResponseError(
                'No json could be decoded from request: Status {}'.format(response.status_code)
                )

        if 'error' in json:
            raise InvalidResponseError(
                'api error excepted: {e[type]} - {e[message]}'.format(e=json['error'])
                )

        if 'message' in json:
            raise InvalidResponseError(
                'api error message excepted: {}'.format(json['message'])
                )

        return json


    @special_apikey_required
    def register(self, username, password, email, newsletter=False):
        """
        Register a new user.

        .. note::
           This function uses a special apikey instead of :attr:`apikey <core.Gfapi.apikey>`

        :param username: The username for the new user
        :param password: The password for the new user
        :param email: The email address for the new user
        :param newsletter: Set to `True` to recieve newsletters

        :return: The user id of the registered user.
        :raise InvalidResponseError: In case of api errors or connection issues
        """
        if "Authorization" in self.header:
            del self.header["Authorization"]

        response = self._get_gfurl(
            self.BASE_URL + "/users",
            mode=self._POST,
            json_payload={
                "agb_accepted" : True,
                "email" : email,
                "newsletter" : newsletter,
                "slug" : username,
                "user_role" : "Standard",
                "remote_id" : self.apikey,
                "password" : password
                }
            )

        return response["id"]


    def login(self, username, password):
        """
        Log into the service and stores the authorization.

        :param username: Your username
        :param password: Your password

        :return: The refresh token for this session
           which can be used in :func:`Gfapi.refresh() <core.Gfapi.refresh>`
        :raise InvalidResponseError: In case of api errors or connection issues
        """
        response = self._get_gfurl(
            self.BASE_URL + "/access_tokens",
            mode=self._POST,
            json_payload={"username" : username, "password" : password}
            )

        if 'type' in response:
            raise UnauthorizedError("Login failed: " + response['type'])

        self.header["Authorization"] = response["access_token"]

        return response["refresh_token"]


    @special_apikey_required
    def refresh(self, refresh_token):
        """
        Refresh authorization using a refresh token.

        .. note::
           This function uses a special apikey instead of :attr:`apikey <core.Gfapi.apikey>`

        :param refresh_token: The refresh token recieved from the last
           :func:`Gfapi.login() <core.Gfapi.login>` or :func:`Gfapi.refresh() <core.Gfapi.refresh>`

        :return: The refresh token for the new session.
        :raise InvalidResponseError: In case of api errors or connection issues
        """
        if "Authorization" in self.header:
            del self.header["Authorization"]

        response = self._get_gfurl(
            self.BASE_URL + "/access_tokens/refresh",
            mode=self._POST,
            json_payload={"refresh_token" : refresh_token}
            )

        self.header["Authorization"] = response["access_token"]

        return response["refresh_token"]


    @authorized
    def post_answer(self, question_id, body, is_html=False):
        """
        Post an answer to a question.

        .. note:: This function requires authorization via
           :func:`Gfapi.login() <core.Gfapi.login>`
           or :func:`Gfapi.refresh() <core.Gfapi.refresh>` first.

        :param question_id: The id of the question the answer will be posted to
        :param body: The content of the question.
        :param is_html: When `body` should be sent as html this has to be set to `True`

        :return: The id of the posted answer.
        :raise InvalidResponseError: In case of api errors or connection issues
        :raise UnauthorizedError: Raised when the authentication key is missing
        """

        if not is_html:
            body = "<p>{}</p>".format(body)

        response = self._get_gfurl(
            self.BASE_URL + "/answers",
            mode=self._POST,
            json_payload={"question_id" : question_id, "body" : body}
            )

        return response["id"]


    @authorized
    def post_comment(self, answer_id, body):
        """
        Post a comment to a answer.

        .. note:: This function requires authorization via
           :func:`Gfapi.login() <core.Gfapi.login>`
           or :func:`Gfapi.refresh() <core.Gfapi.refresh>` first.

        :param answer_id: The id of the answer the comment will be posted to
        :param body: The content of the comment.

        :return: The id of the posted comment.
        :raise InvalidResponseError: In case of api errors or connection issues
        :raise UnauthorizedError: Raised when the authentication key is missing
        """
        response = self._get_gfurl(
            self.BASE_URL + "/comments",
            mode=self._POST,
            json_payload={"answer_id" : answer_id, "body" : body}
            )

        return response["id"]


    @authorized
    def post_question(self, title, body, tags, images=None, subscribe=True):
        """
        Post a new question.

        .. note:: This function requires authorization via
           :func:`Gfapi.login() <core.Gfapi.login>`
           or :func:`Gfapi.refresh() <core.Gfapi.refresh>` first.

        :param title: The title of the question.
        :param body: The body of the question.
        :param tags: A :class:`list` of tags.
        :param images: A :class:`list` of image ids. Images have to be uploaded beforehand.
        :param subscribe: Controls wether notifications related to this question should be recieved.

        :return: The id of the posted comment.
        :raise InvalidResponseError: In case of api errors or connection issues
        :raise UnauthorizedError: Raised when the authentication key is missing
        """

        payload = {
            "body" : body,
            "tags" : tags,
            "subscribe" : subscribe,
            "title" : title,
            "images" : []
            }

        if images is not None:
            payload["images"] = [{"id" : img.id, "description" : img.description} for img in images]

        response = self._get_gfurl(
            self.BASE_URL + "/questions",
            mode=self._POST,
            json_payload=payload
            )

        return response["id"]


    def next_page(self, stream, fields=''):
        """
        Retrieve the next page of a stream.

        :param stream: The stream the next page is retrieved from
        :param fields: The fields to be retrieved

        :return: A new stream representing the next page
        :raise InvalidResponseError: In case of api errors or connection issues
        """
        return self._get_type_stream(stream.TYPE, self._get_gfurl(self.BASE_URL + stream.next, fields))


    def previous_page(self, stream, fields=''):
        """
        Retrieve the previous page of a stream.

        :param stream: The stream the previous page is retrieved from
        :param fields: The fields to be retrieved

        :return: A new stream representing the previous page
        :raise InvalidResponseError: In case of api errors or connection issues
        """
        return self._get_type_stream(stream.TYPE, self._get_gfurl(self.BASE_URL + stream.previous, fields))


    def _get_type_stream(self, objecttype, json_item):
        if objecttype == self._ANSWERS:
            return AnswerStream(json_item)
        elif objecttype == self._QUESTIONS:
            return QuestionStream(json_item)
        elif objecttype == self._TAGS:
            return TagStream(json_item)


    @special_apikey_required
    def search_tags(self, query, fields='', limit=10):
        """
        Retrieve tags starting with `query`.

        .. note::
           This function uses a special apikey instead of :attr:`apikey <core.Gfapi.apikey>`

        :param query: The tag or tag prefix to search for
        :param fields: The fields to be retrieved
        :param limit: The maximum number of results

        :return: Tags starting with `query`
        :raise InvalidResponseError: In case of api errors or connection issues
        """
        return TagStream(
            self._apicall(self._TAGS, fields=fields, prefix=query, limit=limit)
            )


    def recent_questions(self, fields='', limit=10):
        """
        Retrieve the most recent questions.

        :param fields: The fields to be retrieved
        :param limit: The maximum number of results per page

        :return: A :class:`QuestionStream <models.QuestionStream>` of recent questions
        :raise InvalidResponseError: In case of api errors or connection issues
        """
        return QuestionStream(
            self._apicall(self._QUESTIONS, self._LATEST, fields, limit=limit)
            )


    def search_questions(self, query, fields='', limit=10):
        """
        Retrieve search results for `query` as a stream

        :param query: The query for the search
        :param fields: The fields to be retrieved
        :param limit: The maximum number of results per page

        :return: A :class:`QuestionStream <models.QuestionStream>` of results
        :raise InvalidResponseError: In case of api errors or connection issues
        """
        return QuestionStream(
            self._apicall(self._QUESTIONS, self._SEARCH, fields, limit=limit, query=query)
            )


    def question(self, identifier, fields='', id_type=None):
        """
        Retrieve a question from an id or slug.

        :param identifier: The id or slug of the question. Defaults to id.
        :param fields: The fields to be retrieved
        :param id_type: The type of the identifier.

           Has to be :attr:`Gfapi.SLUG <core.Gfapi.SLUG>` to use slugs.

        :return: A :class:`Question <models.Question>` representing the requested question
        :raise InvalidResponseError: In case of api errors or connection issues
        """
        return Question(
            self._apicall(
                self._QUESTIONS,
                id_type + identifier if id_type is not None else identifier,
                fields
                )
            )


    def question_answers(self, identifier, fields=''):
        """
        Retrieve all answers for a question id.

        :param identifier: A question id
        :param fields: The fields to be retrieved

        :return: A :class:`list` of :class:`Answers <models.Answer>`
        :raise InvalidResponseError: In case of api errors or connection issues
        """
        json_item = self._apicall(self._QUESTIONS, u'{}/{}'.format(identifier, self._ANSWERS), fields)
        return [Answer(i) for i in json_item["items"]]


    def user(self, identifier, fields='', id_type=None):
        """
        Retrieve a user from an id, slug or email.

        :param identifier: The id or slug of the user. Defaults to id.
        :param fields: The fields to be retrieved
        :param id_type: The type of the identifier.

           Has to be :data:`Gfapi.SLUG <core.Gfapi.SLUG>` to use slugs
           or :data:`Gfapi.EMAIL <core.Gfapi.EMAIL>` for email requests.

        :return: A :class:`User <models.User>` representing the requested user
        :raise InvalidResponseError: In case of api errors or connection issues
        """
        return User(
            self._apicall(
                self._USERS,
                id_type + identifier if id_type is not None else identifier,
                fields
                )
            )


    def answer(self, identifier, fields=''):
        """
        Retrieve an answer from its id.

        :param identifier: The id of the answer.
        :param fields: The fields to be retrieved

        :return: A :class:`Answer <models.Answer>` representing the requested answer
        :raise InvalidResponseError: In case of api errors or connection issues
        """
        return Answer(
            self._apicall(self._ANSWERS, identifier, fields)
            )


    def comment(self, identifier, fields=''):
        """
        Retrieve an comment from its id.

        :param identifier: The id of the comment.
        :param fields: The fields to be retrieved

        :return: A :class:`Comment <models.Comment>` representing the requested comment
        :raise InvalidResponseError: In case of api errors or connection issues
        """
        return Comment(
            self._apicall(self._COMMENTS, identifier, fields)
            )


    def user_questions(self, identifier, fields=''):
        """
        Retrieve a stream of questions by a user.

        :param identifier: A user id
        :param fields: The fields to be retrieved

        :return: A :class:`QuestionStream <models.QuestionStream>` of the users Questions
        :raise InvalidResponseError: In case of api errors or connection issues
        """
        return QuestionStream(
            self._apicall(self._USERS, u'{}/{}'.format(identifier, self._QUESTIONS), fields)
            )


    def user_answers(self, identifier, fields='', limit=20, mosthelpful=False, id_type=None):
        """
        Retrieve a stream of answers by a user.

        :param identifier: A user id
        :param fields: The fields to be retrieved

        :return: A :class:`AnswerStream <models.AnswerStream>` of the users Questions
        :raise InvalidResponseError: In case of api errors or connection issues
        """
        if mosthelpful:
            json_item = self._apicall(
                self._USERS,
                u'{}/{}'.format(
                    id_type + identifier if id_type is not None else identifier, self._ANSWERS
                    ),
                fields, onlyMostHelpful='True', limit=limit
                )

        json_item = self._apicall(
            self._USERS,
            u'{}/{}'.format(id_type + identifier if id_type is not None else identifier, self._ANSWERS),
            fields, limit=limit
            )

        return AnswerStream(json_item)
