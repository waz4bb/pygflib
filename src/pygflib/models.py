

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


    def __repr__(self):
        return self.raw_link

class Tag():

    def __init__(self,json_item):
        self.name = json_item["name"]
        self.slug = json_item["slug"]
        self.id = json_item["id"]
        self.count = json_item["questions"]["total_count"]


    def __repr__(self):
        return self.name

class FieldContainer():

    def __getattr__(self,field):
        try:
            return self.fields[field]
        except KeyError:
            raise AttributeError("{} not in json response".format(field))


    class Meta:
        abstract = True


class User(FieldContainer):

    def __init__(self,json_item):
        self.fields = {}

        self.fields["avatar"] = Image(json_item["avatar_image"])
        self.fields["cover"] = Image(json_item["cover_image"])

        self.fields["username"] = json_item["display_name"]
        self.fields["slug"] = json_item["slug"]
        self.fields["id"] = json_item["id"]
        self.fields["level"] = json_item["level"]
        self.fields["score"] = json_item["score"]
        self.fields["creation_date"] = json_item["created_at"]
        self.fields["roles"] = json_item["roles"]
        
        self.fields["description"] = json_item["about_me"]
        self.fields["profession"] = json_item["profession"]
        self.fields["birth_date"] = json_item["birthday"]
        self.fields["gender"] = json_item["gender"]
        self.fields["address"] = json_item["address"]
        self.fields["contact_info"] = json_item["contact_information"]
        self.fields["website"] = json_item["website_url"]
        #TODO: add advanced fields

    def __repr__(self):
        return self.fields["username"]


class Comment(FieldContainer):

    def __init__(self,json_item):
        self.user = User(json_item["creator"])
        
        if "parent" in json_item:
            self.parent_id = json_item["parent"]["id"]
        else:
            self.parent_id = None

        self.fields = {}
        self.fields["body"] = json_item["body"]
        self.fields["status"] = json_item["status"]
        self.fields["creation_date"] = json_item["created_at"]
        self.fields["id"] = json_item["id"]
        self.fields["up_votes"] = json_item["up_votes"]["total_count"]


    def __repr__(self):
        return self.fields["body"]

    
class Answer(FieldContainer):

    def __init__(self,json_item):
        self.user = User(json_item["creator"])

        if len(json_item["images"]) == 0:
            self.images = []
        else:
            self.images = [Image(i) for i in json_item["images"]]

        if "items" not in json_item["comments"] or json_item["comments"]["live_count"] == 0:
            self.comments = []
        else:
            self.comments = [Comment(i) for i in json_item["comments"]["items"]]

        self.fields = {}
        self.fields["body"] = json_item["body"]
        self.fields["id"] = json_item["id"]
        self.fields["status"] = json_item["status"]
        self.fields["appreciations"] = json_item["appreciations"]
        self.fields["creation_date"] = json_item["created_at"]
        self.fields["is_most_helpful"] = json_item["is_most_helpful"]
        self.fields["thanks_count"] = json_item["appreciations"]
        self.fields["votes"] = json_item["user_satisfaction_counts"]
        self.fields["views"] = json_item["statistics"]["impressions"]


    def __repr__(self):
        return self.fields["body"]


class Question(FieldContainer):

    def __init__(self,json_item):
        self.user = User(json_item["creator"])
        
        if len(json_item["images"]) == 0:
            self.images = []
        else:
            self.images = [Image(i) for i in json_item["images"]]

        if "items" not in json_item["answers"] or json_item["answers"]["live_count"] == 0:
            self.answers = self.comments = []
        else:
            self.answers = [Answer(i) for i in json_item["answers"]["items"]]
            self.comments = list(chain.from_iterable([i.comments for i in self.answers]))

        self.tags = [Tag(i) for i in json_item["tags"]]

        self.fields = {}
        self.fields["title"] = json_item["title"]
        self.fields["slug"] = json_item["slug"]
        self.fields["body"] = json_item["body"]
        self.fields["id"] = json_item["id"]
        self.fields["creation_date"] = json_item["created_at"]
        self.fields["answer_count"] = json_item["answers"]["total_count"]
        self.fields["answer_count__live"] = json_item["answers"]["live_count"]
        self.fields["up_votes"] = json_item["up_votes"]["total_count"]
        self.fields["has_most_helpful"] = json_item["has_most_helpful_answer"]
        self.fields["most_helpful_status"] = json_item["helpful_answer_status"]
        self.fields["status"] = json_item["status"]
        self.fields["latest_submission"] = json_item["latest_submission"]
        self.fields["latest_submission_date"] = json_item["latest_submission_date"]
        self.fields["latest_activity_date"] = json_item["latest_activity_at"]
        self.fields["views"] = json_item["statistics"]["impressions"]["total"]
        self.fields["google_hits"] = json_item["statistics"]["google_hits"]["last13_months"]


    def __repr__(self):
        return self.fields["title"]
