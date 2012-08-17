# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#     * Rearrange models' order
#     * Make sure each model has one field with primary_key=True
# Feel free to rename the models, but don't rename db_table values or field names.
#
# Also note: You'll have to insert the output of 'django-admin.py sqlcustom [appname]'
# into your database.

from django.db import models

"""
    These models handle the definition of languages and language pairs
"""
class Language(models.Model):
    """
        Each language can have a (short) name, a native name and a full name  
    """
    name = models.CharField(
        max_length=3,
        verbose_name = "Language code",
        help_text="A short name defining the Language. Ideally the ISO language code (e.g. 'en')",
        db_index=True,
        unique=True,
    )
    native_name = models.CharField(
        max_length=120,
        blank = True,
        verbose_name = "Language full name (native)",
        help_text="The original name of the language",
    )
    english_name = models.CharField(
        max_length=120,
        blank = True,
        verbose_name = "Language full name (in English)",
        help_text="The full name of the language in English",
    )
    #whenever this model is called for print functions, display its name
    def __unicode__(self):
        return self.name


class LanguageDirection(models.Model):
    """
        A language direction defines a source and a target language, to be used by 
        bilingual systems and machine translation engines
    """
    name = models.CharField(
        max_length=90,
        help_text="A short name defining the Language Direction, i.e. a source and a target language. \
            Ideally a combination of ISO language codes (e.g. 'de-en')",
        verbose_name = "Language pair codes",
        db_index=True,
        unique=True,
    )
    source_language = models.ForeignKey(
        Language,
        #added to avoid modelling conflict with next field
        related_name = "source_language"   
    )
    target_language = models.ForeignKey(
        Language,
        related_name = "target_language"   
    )
    english_name = models.CharField(
        max_length=90,
        blank=True,
        db_index=True,
        help_text="A long name defining the Language Direction",
        verbose_name = "Language pair long name",
    )
    
    def __unicode__(self):
        return self.name


class System(models.Model):
    """
        A system is an abstract model which only holds the name. It may be inherited by a TranslationSystem, which
        delivers translations and features and has a language direction, or an Analysis System that 
        delivers language-specific analysis either monolingual or bilingual
    """
##    id = models.IntegerField(primary_key=True)    
    name = models.CharField(
        max_length=60,
        verbose_name = "System name",
    )
    long_name = models.CharField(
                                 max_length=120,
                                 blank=True
                                 )

class MonoAnalysisSystem(System):
    """
        A system which produces monolingual analysis and features
        @note: replaced CltSystem, CltSupport
    """
    supported_languages = models.ManyToManyField(Language)

class BiAnalysisSystem(System):
    """
        A system which produces bilingual analysis and features
    """
    supported_language_directions = models.ManyToManyField(LanguageDirection)

class TranslationSystem(System):
    """
        A system that produces machine translation
        @note: replaced MtSystem and MtSystemSupport
    """
    supported_language_directions = models.ManyToManyField(LanguageDirection)



"""
    Corpus-related
"""


class Domain(models.Model):
    name = models.CharField(max_length=60)
    long_name = models.CharField(
                                 max_length=210,
                                 blank=True
                                 )

class Status(models.Model):
    name = models.CharField(max_length=60)
    
class DocumentClass(models.Model):
    name = models.CharField(max_length=60)
    long_name = models.CharField(
                                 max_length=120,
                                 blank=True)

class DocumentSubclass(models.Model): 
    name = models.CharField(max_length=60)
    long_name = models.CharField(
                                 max_length=120,
                                 blank=True
                                 )



class Document(models.Model):
    """
        The basic unit for containing sentences to translate. The documents
        will afterwards be grouped into corpora (see below).
    """
    language = models.ForeignKey(Language)
    filename = models.CharField(
                                max_length = 200,
                                blank=True
                                )


class SourceDocument(Document):
    """
        A document that is to be translated. All the original sentences
        of a document belong to this object. Translations of this document
        are organised with a TranslatedDocument
        @note: replaced TestSet        
    """
    custom_id = models.CharField(
                                 max_length = 200,
                                 help_text="This field should serve for entering a user defined sentence id"
                                 )
    domain = models.ForeignKey(Domain, null=True)
    document_class = models.ForeignKey(DocumentClass, null=True)
    document_subclass = models.ForeignKey(DocumentSubclass, null=True)

    def __unicode__(self):
        return "%s (%s)" % (self.custom_id, self.language.name)

class TranslatedDocument(Document):
    """
        A translation of a document. As a source document can have many
        full translations, this points to a source documents 
        @note: replaced Project
    """
    source = models.ForeignKey(SourceDocument)
    translation_system = models.ForeignKey(
        TranslationSystem,
        help_text = "Choose the translation system that produced this sentence"
    )
    status = models.ForeignKey(Status, null=True)

    def __unicode__(self):
        return "%s (%s: %s => %s)" % (self.source.custom_id, self.system.id,
                                      self.source.language.name, self.language.name)

class Corpus(models.Model):
    """
        A collection of documents
    """
    custom_id = models.CharField(max_length = 200)
    description = models.TextField(
                                   blank=True
                                   )
    documents = models.ManyToManyField(SourceDocument, through="Document2Corpus")
    language = models.ForeignKey(Language)

    def __unicode__(self):
        return "%s (%s)" % (self.custom_id, self.language.name)

class Document2Corpus(models.Model):
    """
        Intermediate table for storing the order of the documents in a corpus
        If http://pypi.python.org/pypi/django-sortedm2m is updated to django
        1.4 we may switch to it
    """
    document = models.ForeignKey(SourceDocument)
    corpus = models.ForeignKey(Corpus)
    order = models.IntegerField()

    class Meta:
        ordering = ['order']


class Sentence(models.Model):
    """
        The base class for the sentences
        Note that we do not want to work with sentences alone, instead we
        work with documents and corpora. As such information like language,
        system, etc. are stored in those classes
    """
    text = models.TextField()
    document = models.ForeignKey(Document)
    

class SourceSentence(Sentence):
    """
        These are the sentences in the SourceDocuments
    """
    custom_id = models.CharField(max_length=200)

    def __unicode__(self):
        return self.custom_id
    

class Translation(Sentence):
    """
        Sentences produced by a translation system
        @note: replaced Content
    """
    source_sentence = models.ForeignKey(SourceSentence)

    def __unicode__(self):
        return "%s - %s" % (self.source_sentence, self.document.language.name)



"""
    The following three models define any kind of feature annotation that can take place on
    a sentence level. Features are produced by any system, which may be a translation system
    or any annotation/analysis software (e.g. Acrolinx). 
    * Each system may provide features on one or many feature sets
    * Each feature set may contain many features
    * Each sentence may be annotated by each of the features with a respective feature value
    @note: replaced Lucy, AcrolinxChecks, Trados
"""
class FeatureSet(models.Model):
    name = models.CharField(
                            max_length=10,
                            unique=True
                            )
    long_name = models.CharField(
                                 max_length=120,
                                 blank=True
                                 )
    source = models.ForeignKey(System)
    
class Feature(models.Model):
    feature_set = models.ForeignKey(FeatureSet)
    name = models.CharField(max_length=120)
    details = models.TextField(
                               blank=True
                               )
    type = models.CharField(
                            blank=True, #not sure
                            max_length=120
                            )

class FeatureValue(models.Model):
    sentence = models.ForeignKey(Sentence)
    feature = models.ForeignKey(Feature)
    value = models.TextField()
    details = models.TextField(
                               blank=True
                               )

