'''
Created on 27 Jul 2012

@author: Patrick Bessler, David Vilar, Eleftherios Avramidis
'''

from django.db import models
from django.contrib.auth.models import User 
from corpus.models import SourceDocument, TranslatedDocument, SourceSentence, Translation, Sentence, TranslationSystem 


APPRAISE_TASK_TYPE_CHOICES = (
  ('1', 'Quality Checking'),
  ('2', 'Ranking'),
  ('3', 'Post-editing'),
  ('4', 'Error classification'),
  ('5', '3-Way Ranking'),
)

class EvaluationCampaign(models.Model):
    """
        We will organzie most of the material in "Evaluation Campaigns",
        e.g. "WMT2012", "TaraXU R2", etc.
    """
    name = models.CharField(max_length = 200)
    #this defines which documents are available to this Evaluation Campaign, but is not binding
    documents = models.ManyToManyField(SourceDocument,
                                       help_text="Select here the documents that will be available for this campaign",
                                       blank=True
                                       )
    description = models.TextField(
                                   blank=True
                                   )

class EvaluationTask(models.Model):
    """
        EvaluationTask contains the various types of evaluation tasks, for each campaign, e.g 
        'post-editing task', 'error classification' etc.
        Tasks can be assigned to users
    """
    name = models.CharField(
        max_length = 200,
        db_index=True,
        unique=True,
        help_text="Please provide a name for this Evaluation Task",                                                        
    )
    type = models.CharField(
        max_length=1,
        choices=APPRAISE_TASK_TYPE_CHOICES,
        db_index=True,
        help_text="Type choice for this evaluation task.",
        verbose_name="Task type"
    )
    campaign = models.ForeignKey(
        EvaluationCampaign,
        help_text="This is the campaign within which the evaluation task is being pursued"
    )
    users = models.ManyToManyField(
        User,
        help_text="Users that will have this evaluation task available"
    )
    description = models.TextField(
        blank=True,
        help_text="(Optional) Text describing this evaluation task.",
    )

    active = models.BooleanField(
        db_index=True,
        default=True,
        help_text="Indicates that this evaluation task is still in use.",
        verbose_name="Active?"
    )
    random_order = models.BooleanField(
        db_index=True,
        default=False,
        help_text="Indicates that items from this evaluation task should be " \
          "shown in random order.",
        verbose_name="Random order?"
    )

    class Meta:
        """
        Metadata options for the EvaluationTask object model.
        """
        ordering = ('name', 'type', 'id')
        verbose_name = "EvaluationTask object"
        verbose_name_plural = "EvaluationTask objects"


class EvaluationItem(models.Model):
    """
       This should contain the items to be evaluated for each one of the tasks. Each item 
       should contain one source sentence and one or more translations.
       Do not crate items here, create directly its subclasses RankItem, PostEditItem, ErrorItem 
    """
    source_sentence = models.ForeignKey(SourceSentence)
    task = models.ForeignKey(EvaluationTask)
    translations = models.ManyToManyField(Translation)    

class EvaluationResult(models.Model):
    """
        Abstract class for modeling basic info for one input of a user as part of the evaluation task 
        Its subclasses RankResult, PostEditedSentence, ErrorResult should be populated by the evaluation interface
    """
    item = models.ForeignKey(EvaluationItem)
    timestamp = models.DateTimeField()
    duration = models.TimeField(blank=True, null=True, editable=False)
    user = models.ForeignKey(User, db_index=True)

    class Meta:
        """
        Metadata options for the EvaluationResult object model.
        """
        ordering = ('id',)
        verbose_name = "EvaluationResult object"
        verbose_name_plural = "EvaluationResult objects"

    def readable_duration(self):
        """
        Returns a readable version of the this EvaluationResult's duration.
        """
        return '{}'.format(self.duration)
    
#### RANKING TASK
class RankResult(EvaluationResult):
    """
        The rank (order of preference) for a selected system in a ranking list
    """
    translation = models.ForeignKey(Translation)
    rank = models.IntegerField() 

#### POSTEDITING TASK


class PostEditedSentence(EvaluationResult, Sentence):
    """
        Once the user has finished post-editing this should also be stored
        as an evaluation result, containing timing information
    """
    original_sentence =  models.ForeignKey(Translation)


#ErrorClassificationTask

class ErrorClass(models.Model):
    """
        This is part of the error classifications set up. It defines the
        error classes that will be available to choose from. Each error
        classification task can define a different set of error classes
    """
    name = models.CharField(max_length=300)
    task = models.ForeignKey(EvaluationTask)

class ErrorResult(EvaluationResult):
    """
        Once an error class has been chosen for a word, this is stored here 
    """    
    error_class = models.ForeignKey(ErrorClass)
    word_pos = models.IntegerField()
    
