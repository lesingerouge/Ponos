# system imports
import cPickle
# framework imports
import bson
# app imports

class ValidationError(Exception):
    pass


class BaseField(object):

    def __init__(self, dbfield=None, verbose=None, default=None, unique=False, value=None, validate=None, required=False):
        self.dbfield = dbfield
        self.verbose = verbose
        self.default = default
        self.unique = unique
        self.required = required
        self.validate = validate
        self._value = None

        if not value:
            if hasattr(default,"__call__"):
                self._value = default()
            elif default is not None:
                self._value = default
        else:
            self._value = value


    def __set__(self, value):
        if self.validate is not None:
            if not isinstance(value,self.validate):
                raise AttributeError("Value '%s' for item '%s' is not valid." % (value,self.dbfield))

        self._value = value

    def __get__(self):
        return self._value

    value = property(__get__,__set__)

    def __repr__(self):
        return str({item: self.__dict__[item] for item in self.__dict__})

    def validates(self):
        valid = True

        if self.validate is not None:
            if not isinstance(self._value,self.validate):
                raise ValidationError("Item '%s' is not valid." % self.dbfield)

        return valid

    def is_required(self):
        valid = True

        if self.required:
            if not self._value and not self.default:
                raise ValidationError("Item '%s' is required." % self.dbfield)

        return valid

    def to_dict(self):
        return {self.dbfield:self._value}


class BaseDocument(object):

    fromdict = None
    db = None
    collection = None

    def __init__(self, frompickle=None, values=None, **kwargs):
        
        if self.fromdict and not frompickle:
            from_dict = self.fromdict
        elif frompickle:
            from_dict = cPickle.loads(frompickle)
        else:
            raise AttributeError("No class definitions, cannot build instance.")
        
        for item in from_dict:
            #TODO: fix this by changing names of private attributes (prepend _)
            if item in ['db','collection','fromdict']:
                raise AttributeError("Field name conflict on field %s! Attribute is private!" % item)
            else:
                setattr(self,item,BaseField(**from_dict[item]))

        if not "_id" in self.__dict__ or not self._id:
            setattr(self,"_id",BaseField(dbfield="_id",unique=True,required=True))
       
        if values:
            for k in self.__dict__:
                temp = getattr(self,k)
                for item in values:
                    if k == item or temp.dbfield == item:
                        temp.value = values[item]

        # if kwargs and not values:
        #     if isinstance(kwargs,dict) and len(kwargs) > 1:
        #         for k in self.__dict__:
        #             for item in kwargs:
        #                 if item in ['db','collection','fromdict']:
        #                     raise AttributeError("Field name conflict! Cannot use reserved words: db, collection, fromdict!")
        #                 temp = getattr(self,k)
        #                 if k == item or temp.dbfield == item:
        #                     temp.value = kwargs[item]

        self.create_indexes()
        

    def _check_internals(self):

        if not self.db or not self.collection:
            raise AttributeError("Db or Collection not set.")

        return True

    
    def _get_obj_attrs(self):

        items = []
        for item in self.__dict__:
            temp = getattr(self,item)
            items.append(temp)

        return items


    def _reload(self):

        new_values = self.db[self.collection].find_one({"_id":bson.objectid.ObjectId(self._id.value)})
        for k in new_values:
            for item in self._get_obj_attrs():
                if item.dbfield == k:
                    item.value = new_values[k]


    def to_dict(self):

        return {item:getattr(self,item).value for item in self.__dict__}


    def create_indexes(self):

        self._check_internals()
        
        for item in self._get_obj_attrs():
            if item.unique:
                self.db[self.collection].create_index([(item.dbfield, 1)],unique=True)


    def save(self):

        self._check_internals()

        insertion_data = {}

        for item in self._get_obj_attrs():
            print item
            if item.dbfield != "_id" and item.validates() and item.is_required():
                insertion_data.update(item.to_dict())

        print insertion_data
            
        if insertion_data and not self._id.value:
            self._id.value = self.db[self.collection].insert_one(insertion_data).inserted_id
        elif insertion_data and self._id.value:
            self.db[self.collection].update_one({"_id":bson.objectid.ObjectId(self._id.value)},{"$set":insertion_data})
        else:
            raise AttributeError("Nothing to insert.")


    def delete(self):

        self._check_internals()

        if not self._id.value:
            raise ValidationError("Object is not saved, cannot delete.")

        self.db[self.collection].delete_one({"_id":bson.objectid.ObjectId(self._id.value)})



    def update(self,update):

        if not self._id.value:
            raise AttributeError("Document not saved.")
        else:
            self.db[self.collection].update_one({"_id":bson.objectid.ObjectId(self._id.value)},update)
            self._reload()


    def fill_form(self,_form=None):

        if _form:
            form = _form
        else:
            form = self.get_form()

        for item in form.data:
            if item != "submit":
                temp = getattr(self,item,None)
                if temp:
                    formitem = getattr(form,item)
                    formitem.data = temp.value

        return form


    def populate_from_form(self,form):

        for item in form.data:
            temp = getattr(self,item,None)
            if temp and temp.value != form.data[item]:
                temp.value = form.data[item]

        
    @classmethod
    def get(cls,_filter,raw=False):

        if raw:
            final_filter = _filter
        else:
            final_filter = {}
            if cls.fromdict:
                for item in _filter:
                    temp = cls.fromdict.get(item)
                    if temp:
                        final_filter.update({temp["dbfield"]:_filter[item]})
                    if item == "_id":
                        final_filter.update({"_id":bson.objectid.ObjectId(_filter["_id"])})

        values = cls.db[cls.collection].find_one(final_filter)
        if not values:
            raise AttributeError("Cannot find user.")
            
        user = cls(values=values)
                
        return user

    @classmethod
    def connection(cls):

        if cls.db and cls.collection:
            return cls.db[cls.collection]


    @classmethod
    def get_form(cls):

        return NotImplemented()





