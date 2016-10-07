import requests
import re
from itertools import chain

from lxml import html

from pygflib.models import Question,Answer,Comment,User

class Gfapi():
    
    Q = 'questions'
    U = 'users'
    C = 'comments'
    A = 'answers'
    T = 'tags'
    
    LATEST = 'latest'
    SEARCH = 'search'
    SLUG = 'slug:'
    
    def __init__(self):
        
        self.get_apikey()
        
    def get_apikey(self,header=None):
        if header is None:
            header = {'User-Agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:39.0) Gecko/20100101 Firefox/39.0',
                       'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                       'Accept-Language' : 'de,en-US;q=0.7,en;q=0.3',
                       'DNT' : '1',
                       'referer' : 'http://www.gutefrage.net',
                       'Connection' : 'keep-alive',
                       'Origin' : 'http://www.gutefrage.net',
                       'X-Api-Version' : '1'
                       }
        
        r = requests.get('http://www.gutefrage.net/frage_hinzufuegen',headers = header)
        self.apikey = re.search("key: '([^']+)'",html.document_fromstring(r.text).xpath('//script[1]')[0].text).group(1)
        
        self.header = header
        self.header['X-Api-Key'] = self.apikey
        
        return self.apikey
    
    
    #TODO: improve this method to work better with tag queries
    def _apicall(self,objecttype,identifier=None,fields='',**kwargs):
        if id == self.SEARCH and 'query' not in kwargs:
            raise Exception('Searching requieres a query')
      
        apiurl = 'https://api.gutefrage.net/{}{}{}?fields={}{}'.format(
                objecttype,
                '/' if identifier else '',
                identifier,
                fields,
                ''.join(['&{}={}'.format(param,kwargs.get(param)) for param in kwargs]) if len(kwargs) > 0 else ''
                )

        return self.get_gfurl(apiurl,fields)
    
        
    def get_gfurl(self,apiurl,fields=''):
        r = requests.get(apiurl,params = {'fields' : fields},headers = self.header)
        try:
            json = r.json()
            return json
        except ValueError:
            return None
    
    
    def search_tags(self,query,fields='',limit=10):
        return self._apicall(self.T,fields=fields,prefix=query,limit=limit)
    
    
    def get_recent_questions(self,fields='',limit=10):
        return self._apicall(self.Q,self.LATEST,fields,limit=limit)
    
    
    def search_questions(self,query,fields='',limit=10):
        return self._apicall(self.Q,self.SEARCH,fields,limit=limit,query=query)
    
    
    def get_question(self,identifier,fields='',is_slug=False):
        return Question(
                self._apicall(self.Q,(self.SLUG + identifier) if is_slug else identifier,fields)
                )
    
    
    def get_question_answers(self,identifier,fields='',is_slug=False):
        return self._apicall(self.Q,u'{}/{}'.format((self.SLUG + identifier) if is_slug else identifier,self.A),fields)
    
    
    def get_user(self,identifier,fields='',is_slug=False):
        return User(
                self._apicall(self.U,(self.SLUG + identifier) if is_slug else identifier,fields)
                )
    
    
    def get_answer(self,identifier,fields=''):
        return Answer(
                self._apicall(self.A,identifier,fields)
                )
    
    
    def get_comment(self,identifier,fields=''):
        return Comment(
                self._apicall(self.C,identifier,fields)
                )
    
    
    def get_user_questions(self,identifier,fields=''):
        return self._apicall(self.U,u'{}/{}'.format(identifier,self.Q),fields)
        
   
    def get_user_answers(self,identifier,fields='',limit=20,mosthelpful=False,is_slug=False):
        if mosthelpful:
            return self._apicall(
                    self.U,
                    u'{}/{}'.format((self.SLUG + identifier) if is_slug else identifier,self.A),
                    fields,onlyMostHelpful='True',limit=limit
                    )
        
        return self._apicall(
                self.U,
                u'{}/{}'.format((self.SLUG + identifier) if is_slug else identifier,self.A)
                ,fields,limit=limit
                )
