API core
********

.. automodule:: core


Gfapi
=====

General Usage
-------------

::

   from pygflib import Gfapi

   #creates a new api instance with a new key retrieved from gutefrage.net
   api = Gfapi()

   #fields to retrieve only ids titles and the username of the creator
   #links are required for pagination
   fields = 'links,items(id,title,creator(display_name))'

   #get a question stream with the 100 most recent questions
   recent_stream = api.get_recent_questions(fields,100)

   #get the most recent question's answers
   answers = api.question_answers(recent_stream[0].id,'id,body')
   print(answers[0].body)

   #log in and post a comment to the first answer
   api.login("username","password")
   api.post_comment(answers[0].id,input("Enter your comment: "))


API
---

.. autoclass:: core.Gfapi
   :members:


Exceptions
==========

.. autoexception:: core.InvalidResponseError
.. autoexception:: core.UnauthorizedError

Decorators
==========

.. autofunction:: core.authorized
.. autofunction:: core.special_apikey_required
