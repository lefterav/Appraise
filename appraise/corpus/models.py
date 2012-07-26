# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#     * Rearrange models' order
#     * Make sure each model has one field with primary_key=True
# Feel free to rename the models, but don't rename db_table values or field names.
#
# Also note: You'll have to insert the output of 'django-admin.py sqlcustom [appname]'
# into your database.

from django.db import models
from django.contrib.admin.util import help_text_for_field
"""
    Language
"""

class Language(models.Model):
#    id = models.IntegerField(primary_key=True)
    name = models.CharField(
                            max_length=3,
                            help_text_for_field="A short name defining the Language. Ideally the ISO language code",
                            verbose_name = "Language code"
                            )
    long_name = models.CharField(max_length=120)
    class Meta:
        db_table = u'languages'
    
    def __unicode__(self):
        return self.name

class LanguageDirection(models.Model):
##    id = models.IntegerField(primary_key=True)
    source_language = models.ForeignKey(
      Language,
      related_name = "source_language"   
    )
    target_language = models.ForeignKey(
      Language,
      related_name = "target_language"   
    )
    name = models.CharField(max_length=90)
    class Meta:
        db_table = u'language_directions'


"""
    System is an abstract table which only holds the name. We may have an TranslationSystem, which
    delivers translations and features and has a language direction, or an analysis system that 
    delivers language-specific analysis either monolingual or bilingual
"""
class System(models.Model):
##    id = models.IntegerField(primary_key=True)    
    name = models.CharField(max_length=60)
    long_name = models.CharField(max_length=120)

class MonoAnalysisSystem(System):
    supported_languages = models.ManyToManyField(Language)

class BiAnalysisSystem(System):
    supported_language_directions = models.ManyToManyField(LanguageDirection)

class TranslationSystem(System):
    supported_language_directions = models.ManyToManyField(LanguageDirection)
    
    class Meta: #@TODO: fix db_tables for models missing, if needed
        db_table = u'mt_systems'




"""
    Corpus-related
"""




class Domain(models.Model):
#    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=60)
    long_name = models.CharField(max_length=210)
    class Meta:
        db_table = u'domains'

class Status(models.Model):
    name = models.CharField(max_length=60)
    
    
    
class DocumentClass(models.Model):
#    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=60)
    long_name = models.CharField(max_length=120)
    class Meta:
        db_table = u'project_class'

class DocumentSubclass(models.Model):
#    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=60)
    long_name = models.CharField(max_length=120)
    class Meta:
        db_table = u'project_subclass'
#
#class ProjectFilename(models.Model):
##    id = models.IntegerField(primary_key=True)
#    name = models.CharField(max_length=300)
#    class Meta:
#        db_table = u'project_filename'
        

################################################################################
# The basic unit for containing sentences to translate. The documents
# will afterwards be grouped into corpora (see below).
class Document(models.Model):
    language = models.ForeignKey(Language)
    filename = models.CharField(max_length = 200)
#    campaigns = models.ManyToManyField("EvaluationCampaign")



# A document that is to be translated
class SourceDocument(Document):
    custom_id = models.CharField(max_length = 200)
    domain = models.ForeignKey(Domain)
    document_class = models.ForeignKey(DocumentClass)
    document_subclass = models.ForeignKey(DocumentSubclass)

    def __unicode__(self):
        return "%s (%s)" % (self.custom_id, self.language.name)

# A translation of a document
class TranslatedDocument(Document):
    source = models.ForeignKey(SourceDocument)
    status = models.ForeignKey(Status)

    def __unicode__(self):
        return "%s (%s: %s => %s)" % (self.source.custom_id, self.system.id,
                                      self.source.language.id, self.language.name)

# A collection of documents
class Corpus(models.Model):
    custom_id = models.CharField(max_length = 200)
    description = models.TextField()
    documents = models.ManyToManyField(SourceDocument, through="Document2Corpus")
#    campaigns = models.ManyToManyField(EvaluationCampaign)
    language = models.ForeignKey(Language)

    def __unicode__(self):
        return "%s (%s)" % (self.custom_id, self.language.name)

# Intermediate table for storing the order of the documents in a corpus
# If http://pypi.python.org/pypi/django-sortedm2m is updated to django
# 1.4 we may switch to it
class Document2Corpus(models.Model):
    document = models.ForeignKey(SourceDocument)
    corpus = models.ForeignKey(Corpus)
    order = models.IntegerField()

    class Meta:
        ordering = ['order']

################################################################################
# The base class for the sentences
# Note that we do not want to work with sentences alone, instead we
# work with documents and corpora. As such information like language,
# system, etc. are stored in those classes
class Sentence(models.Model):
    text = models.TextField()
    document = models.ForeignKey(Document)


# These are the sentences in the SourceDocuments
class SourceSentence(Sentence):
    custom_id = models.CharField(max_length=200)

    def __unicode__(self):
        return self.custom_id

# Sentences produced by a translation system
class Translation(Sentence):
    sourceSentence = models.ForeignKey(SourceSentence)
    mt_system = models.ForeignKey(TranslationSystem)

    def __unicode__(self):
        return "%s - %s" % (self.sourceSentence, self.document.language.name)








# This has been replaced by Document
#class Testsets(models.Model):
##    id = models.IntegerField(primary_key=True)
#    name = models.CharField(max_length=90)
#    long_name = models.CharField(max_length=150)
#    class Meta:
#        db_table = u'testsets'




"""
    The following three models define any kind of feature annotation that can take place on
    a sentence level. Features are produced by any system, which may be a translation system
    or any annotation/analysis software (e.g. Acrolinx). 
    * Each system may provide features on one or many feature sets
    * Each feature set may contain many features
    * Each sentence may be annotated by each of the features with a respective feature value
"""
class FeatureSet(models.Model):
#    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=120)
    name = models.CharField(max_length=10)
    source = models.ForeignKey(System)
    
class Feature(models.Model):
#    id = models.IntegerField(primary_key=True)
    feature_set = models.ForeignKey(FeatureSet)
    name = models.CharField(max_length=120)
    details = models.TextField()
    type = models.CharField(max_length=120)

class FeatureValue(models.Model):
#    id = models.IntegerField(primary_key=True)
    sentence = models.ForeignKey(Sentence)
    feature = models.ForeignKey(Feature)
    value = models.TextField()
    details = models.TextField()




# I guess this is replaced by the ManyToManyField of TranslationSystem
#class MtSupport(models.Model):
##    id = models.IntegerField(primary_key=True)
#    lang_dir = models.ForeignKey(LanguageDirection)
#    mt_system = models.ForeignKey(TranslationSystem)
#    supported = models.IntegerField()
#    class Meta:
#        db_table = u'mt_support'




"""
    It is suggested that the following models be removed and their contents
    be transferred in the Feature and FeatureSet model
"""
#class AcrolinxChecks(models.Model):
##    id = models.IntegerField(primary_key=True)
#    type = models.CharField(max_length=120)
#    error = models.CharField(max_length=765)
#    error_detailed = models.CharField(max_length=765)
#    sentence = models.ForeignKey(Sentence)
#    mt_system = models.ForeignKey(TranslationSystem)
#    class Meta:
#        db_table = u'acrolinx_checks'


#class Lucy(models.Model):
##    id = models.IntegerField(primary_key=True)
#    sentence = models.ForeignKey(Sentence)
#    phrs_analysis = models.IntegerField()
#    phrs_transfer = models.IntegerField()
#    phrs_generation = models.IntegerField()
#    ukw_src = models.TextField()
#    ukw_trg = models.TextField()
#    context_sentence = models.TextField()
#    tree_analysis = models.TextField()
#    tree_transfer = models.TextField()
#    tree_generation = models.TextField()
#    ukw_count = models.IntegerField()
#    alternatives_count = models.IntegerField()
#    morph_count = models.IntegerField()
#    subject_areas = models.TextField()
#    class Meta:
#        db_table = u'lucy'
#
#class Trados(models.Model):
##    id = models.IntegerField(primary_key=True)
#    sentenceid = models.ForeignKey(Sentence, db_column='sentenceID') # Field name made lowercase.
#    match_value = models.IntegerField()
#    class Meta:
#        db_table = u'trados'
#        


"""
    @TODO: read some documentation for the use of these
"""
class CltSystem(models.Model):
#    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=60)
    long_name = models.CharField(max_length=120)
    class Meta:
        db_table = u'clt_systems'

class CltSupport(models.Model):
#    id = models.IntegerField(primary_key=True)
    clt_system = models.ForeignKey(CltSystem)
    lang = models.ForeignKey(Language)
    supported = models.IntegerField()
    class Meta:
        db_table = u'clt_support'




"""
    Evaluation-related
"""

# Replaced with Translation 

#class Content(models.Model):
##    id = models.IntegerField(primary_key=True)
#    sentence = models.ForeignKey(Sentence)
#    project = models.ForeignKey(Project)
#    project_filename = models.ForeignKey(ProjectFilename)
#    mt_system = models.ForeignKey(TranslationSystem)
#    content_target = models.TextField()
#    class Meta:
#        db_table = u'content'




        





#class Project(models.Model): #replaced by SourceDocument
##    id = models.IntegerField(primary_key=True)
#    lang_dir = models.ForeignKey(LanguageDirection)
#    status = models.ForeignKey(Status)
#    name = models.CharField(max_length=150)
#    long_name = models.CharField(max_length=300)
#    project_class = models.ForeignKey(ProjectClass)
#    project_subclass = models.ForeignKey(ProjectSubclass)
#    domain = models.ForeignKey(Domain)
#    project_filename = models.ForeignKey(ProjectFilename)
#    class Meta:
#        db_table = u'projects'



#class Eval(models.Model):
##    id = models.IntegerField(primary_key=True)
##    content = models.ForeignKey(Content)
#    rank = models.IntegerField()
#    bleu = models.IntegerField()
#    per = models.IntegerField()
##    trados_match_rate = models.ForeignKey(Trados, db_column='trados_match_rate')
#    project_filename = models.ForeignKey(ProjectFilename)
#    eval_round_id = models.IntegerField()
#    testset = models.ForeignKey(Testsets)
#    rank_user = models.CharField(max_length=765)
#    rank_id = models.IntegerField()
#    lang_dir = models.ForeignKey(LanguageDirection)
#    mt_system = models.ForeignKey(TranslationSystem)
#    pe_id = models.IntegerField()
#    pe_user = models.CharField(max_length=765)
#    pe_lev = models.IntegerField()
#    pe_lev_diff = models.IntegerField()
#    classification_user = models.CharField(max_length=765)
#    error_class = models.ForeignKey(ErrorClass)
#    project = models.ForeignKey(Project)
#    
#    class Meta:
#        db_table = u'eval'

"""
    Our evaluation
"""

################################################################################
# We will organzie most of the material in "Evaluation Campaigns",
# e.g. "WMT2012", "TaraXU R2", etc.

class EvalCampaign(models.Model):
    name = models.CharField(max_length = 200)
    #this defines which documents are available to this Evaluation Campaign, but is not binding
    documents = models.ManyToManyField(SourceDocument)
    description = models.TextField()

class EvalTask(models.Model):
    name = models.CharField(max_length = 200)
    campaign = models.ForeignKey(EvalCampaign)
    domain = models.ForeignKey(Domain)

#This helps us define an item for a task
class EvalItem(models.Model):
    source_sentence = models.ForeignKey(SourceSentence)
    translations = models.ManyToManyField(Translation)
    task = models.ForeignKey(EvalTask)

class EvalResult(models.Model):
    item = models.ForeignKey(EvalItem)
    timestamp = models.DateTimeField()
    
class PostEditedSentence(Sentence):
    original_sentence =  models.ForeignKey(Translation)

class PostEditResult(EvalResult):
    postedited_sentence = models.ForeignKey(PostEditedSentence)

class ErrorClass(models.Model):
    name = models.CharField(max_length=300)
    task = models.ForeignKey(EvalTask)
    
    

    

    


        
"""
    Selection mechanism
"""
# @TODO: This table is not very handy for the statistical experiments
# because rules are not necessarily fixed.
class Rule(models.Model):
#    id = models.IntegerField(primary_key=True)
    rule_name = models.CharField(max_length=180)
    description = models.CharField(max_length=765)
    class Meta:
        db_table = u'rules'


class Publication(models.Model):
#    id = models.IntegerField(primary_key=True)
    project = models.ForeignKey(TranslatedDocument)
    rule = models.ForeignKey(Rule)
    creation_date = models.DateField()
    change_date = models.DateField()
    sentence = models.ForeignKey(SourceSentence)
    mt_system = models.ForeignKey(TranslationSystem)
    class Meta:
        db_table = u'publications'



