from itertools import chain


class Image():


    SMALL = "small"
    THUMBNAIL = "thumbnail" #same size as SMALL
    MEDIUM = "medium"
    K2 = "2000"
    K3 = "3000"
    ORIGINAL = "original" #full size uncropped
    
    #Not confirmed to work
    M4 = "M4_160"
    MOBILE = "mobile"
    DESKTOP = "desktop"


    def __init__(self,json_item):
        self.id = json_item["id"]
        self.raw_link = json_item["url"]
        self.description = json_item["description"]


    def link(self,size):
        return self.raw_link.replace("%size%",size)


class FieldContainer():


    def __getattr__(self,field):
        try:
            return self.fields[field]
        except KeyError:
            raise AttributeError("{} not in json response".format(field))


    class Meta:
        abstract = True


class Tag(FieldContainer):

    FIELDS = [
            "name",
            "slug",
            "id"
            ]

    def __init__(self,json_item):
        
        self.fields = {}

        for field in self.FIELDS:
            if field in json_item:
                self.fields[field] = json_item[field]

        if "questions" in json_item:
            self.fields["count"] = json_item["questions"]["total_count"]


class User(FieldContainer):
    

    FIELDS = [
            "roles",
            "slug",
            "id",
            "level",
            "score",
            "created_at",
            "profession"
            "gender",
            "address",
            "contact_information",
            "birthday"
            ]

    FIELDMAPPINGS = {
            "website_url" : "website",
            "about_me" : "description",
            "display_name" : "username"
            } 


    def __init__(self,json_item):
        self.fields = {}
        
        if "avatar_image" in json_item:
            self.fields["avatar"] = Image(json_item["avatar_image"])

        if "cover_image" in json_item:
            self.fields["cover"] = Image(json_item["cover_image"])

        for field,mapping in self.FIELDMAPPINGS.items():
            if field in json_item:
                self.fields[mapping] = json_item[field]

        for field in self.FIELDS:
            if field in json_item:
                self.fields[field] = json_item[field]

        #TODO: add advanced fields


class Comment(FieldContainer):
    

    FIELDS = [
            "body",
            "status",
            "created_at",
            "id"
            ]


    def __init__(self,json_item):
        self.fields = {}

        if "creator" in json_item:
            self.fields["user"] = User(json_item["creator"])
        
        if "parent" in json_item:
            self.fields["comments"] = json_item["parent"]["id"]

        if "up_votes" in json_item:
            self.fields["up_votes"] = json_item["up_votes"]["total_count"]

        for field in self.FIELDS:
            self.fields[field] = json_item[field]

    
class Answer(FieldContainer):

    
    FIELDS = [
            "body",
            "id",
            "status",
            "created_at",
            "is_most_helpful"
            ]


    def __init__(self,json_item):

        self.fields = {}

        if "creator" in json_item:
            self.fields["user"] = User(json_item["creator"])

        if "appreciations" in json_item:
            self.fields["appreciations"] = json_item["appreciations"]["total_count"]

        if "images" in json_item:
            self.fields["images"] = [Image(i) for i in json_item["images"]]
        else:
            self.fields["images"] = []

        self.fields["comments"] = []

        if "comments" in json_item:
            if "items" in json_item["comments"]:
                self.fields["comments"] = [Comment(i) for i in json_item["comments"]["items"]]

            if "live_count" in json_item:
                self.fields["comment_count"] = json_item["live_count"]

        if "statistics" in json_item and "impressions" in json_item["statistics"]:
            self.fields["views"] = json_item["statistics"]["impressions"]["total"]

        if "user_satisfaction_counts" in json_item:
            self.fields["up_votes"] = json_item["user_satisfaction_counts"]["positive_count"]
            self.fields["down_votes"] = json_item["user_satisfaction_counts"]["negative_count"]
            self.fields["score"] = self.up_votes - self.down_votes

        for field in self.FIELDS:
            if field in json_item:
                self.fields[field] = json_item[field]


class Question(FieldContainer):


    FIELDS = [
            "title",
            "slug",
            "body",
            "id",
            "created_at",
            "has_most_helpful_answer",
            "helpful_answer_status",
            "status",
            "latest_submission",
            "latest_submission_date",
            "latest_activity_at"
            ]
    

    def __init__(self,json_item):

        self.fields = {}

        if "images" in json_item:
            self.fields["images"] = [Image(i) for i in json_item["images"]]
        else:
            self.fields["images"] = []
        
        self.fields["answers"] = self.fields["comments"] = []

        if "answers" in json_item:
            if "items" in json_item["answers"]:
                self.fields["answers"] = [Answer(i) for i in json_item["answers"]["items"]]
                self.fields["comments"] = list(chain.from_iterable([i.comments for i in self.answers]))

            if "live_count" in json_item["answers"]:
                self.fields["answer_count"] = json_item["answers"]["total_count"]

        if "tags" in json_item:
            self.fields["tag"] = [Tag(i) for i in json_item["tags"]]

        if "creator" in json_item:
            self.fields["user"] = User(json_item["creator"])

        
        if "up_votes" in json_item:
            self.fields["up_votes"] = json_item["up_votes"]["total_count"]

        if "statistics" in json_item and "impressions" in json_item["statistics"]:
            self.fields["views"] = json_item["statistics"]["impressions"]["total"]

        for field in self.FIELDS:
            if field in json_item:
                self.fields[field] = json_item[field]


class AbstractStream():


    def __init__(self,json_item):
        if "total_count" in json_item:
            self.total_count = json_item["total_count"]


    def next():
        """ unimplemented """


    def previous():
        """ unimplemented """


    def __getitem__(self,index):
        return self.items[index]


    def __iter__(self):
        for i in self.items:
            yield i


    def __len__(self):
        return len(self.items)


    def __repr__(self):
        return "[{}]".format(", ".join([repr(i) for i in self.items]))


class QuestionStream(AbstractStream):


    def __init__(self,json_item):
        super().__init__(json_item)
        self.items = [Question(i) for i in json_item["items"]]


class AnswerStream(AbstractStream):


    def __init__(self,json_item):
        super().__init__(json_item)
        self.items = [Answer(i) for i in json_item["items"]]


class TagStream(AbstractStream):


    def __init__(self,json_item):
        super().__init__(json_item)
        self.tags = [Tag(i) for i in json_item["items"]]
