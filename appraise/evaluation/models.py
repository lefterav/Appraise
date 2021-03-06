# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@dfki.de>
"""
import logging
import uuid

from xml.etree.ElementTree import Element, fromstring, ParseError, tostring

from django.dispatch import receiver

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import models
from django.template import Context
from django.template.loader import get_template

from appraise.settings import LOG_LEVEL, LOG_HANDLER
from appraise.utils import datetime_to_seconds

import corpus.models as corpusM

# Setup logging support.
logging.basicConfig(level=LOG_LEVEL)
LOGGER = logging.getLogger('appraise.evaluation.models')
LOGGER.addHandler(LOG_HANDLER)


APPRAISE_TASK_TYPE_CHOICES = (
  ('1', 'Quality Checking'),
  ('2', 'Ranking'),
  ('3', 'Select-and-post-edit'),
  ('4', 'Error classification'),
  ('5', '3-Way Ranking'),
  ('6', 'Post-edit-all')
)

class EvaluationTask(models.Model):
    """
    Evaluation Task object model.
    """
    task_id = models.CharField(
      max_length=32,
      db_index=True,
      unique=True,
      editable=False,
      help_text="Unique task identifier for this evaluation task.",
      verbose_name="Task identifier"
    )

    task_name = models.CharField(
      max_length=100,
      db_index=True,
      help_text="Unique, descriptive name for this evaluation task.",
      unique=True,
      verbose_name="Task name"
    )

    task_type = models.CharField(
      max_length=1,
      choices=APPRAISE_TASK_TYPE_CHOICES,
      db_index=True,
      help_text="Type choice for this evaluation task.",
      verbose_name="Task type"
    )

    # This was derived from task_xml and NOT stored in the database.
    task_attributes = {}

    description = models.TextField(
      blank=True,
      help_text="(Optional) Text describing this evaluation task.",
      verbose_name="Description"
    )

    users = models.ManyToManyField(
      User,
      blank=True,
      db_index=True,
      null=True,
      help_text="(Optional) Users allowed to work on this evaluation task."
    )

    corpus = models.ForeignKey(corpusM.Corpus,null=True)
    
    systems = models.ManyToManyField(corpusM.TranslationSystem)

    targetLanguage = models.ForeignKey(corpusM.Language,null=True)

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

    context_length = models.IntegerField(
        default=1,
        help_text="Length of the context to display"
    )

    class Meta:
        """
        Metadata options for the EvaluationTask object model.
        """
        ordering = ('task_name', 'task_type', 'task_id')
        verbose_name = "EvaluationTask object"
        verbose_name_plural = "EvaluationTask objects"
    
    def __init__(self, *args, **kwargs):
        """
        Makes sure that self.task_attributes are available.
        """
        super(EvaluationTask, self).__init__(*args, **kwargs)
        
        if not self.task_id:
            self.task_id = self.__class__._create_task_id()
    
    def __unicode__(self):
        """
        Returns a Unicode String for this EvaluationTask object.
        """
        #return u'<evaluation-task id="{0}">'.format(self.id)
        return '%s %s %s' % (self.task_id, self.task_name, self.get_task_type_display())
    
    @classmethod
    def _create_task_id(cls):
        """Creates a random UUID-4 32-digit hex number for use as task id."""
        new_id = uuid.uuid4().hex
        while cls.objects.filter(task_id=new_id):
            new_id = uuid.uuid4().hex
        
        return new_id
    
    # Function to be implemented by the subclasses
    def generateItems(self, *args, **kwargs):
        pass
   
    def get_absolute_url(self):
        """
        Returns the URL for this EvaluationTask object instance.
        """
        task_handler_view = 'evaluation.views.task_handler'
        kwargs = {'task_id': self.task_id}
        return reverse(task_handler_view, kwargs=kwargs)
    
    def reload_dynamic_fields(self):
        """
        Reloads task_attributes from self.task_xml contents.
        """
        pass
        # If a task_xml file is available, populate self.task_attributes.
        #if self.task_xml:
        #    try:
        #        _task_xml = fromstring(self.task_xml.read())
        #        self.task_attributes = {}
        #        for key, value in _task_xml.attrib.items():
        #            self.task_attributes[key] = value
        #    
        #    except ParseError:
        #        self.task_attributes = {}
    
    def get_status_header(self):
        """
        Returns the header template for this type of EvaluationTask objects.
        """
        # pylint: disable-msg=E1101
        _task_type = self.get_task_type_display()
        _header = ['Overall completion', 'Average duration']
        
        return _header
    
    def get_status_for_user(self, user=None):
        """
        Returns the status information with respect to the given user.
        """
        # pylint: disable-msg=E1101
        _task_type = self.get_task_type_display()
        _status = []
        
        # Compute completion status for this task and the given user.
        _items = EvaluationItem.objects.filter(task=self).count()
        _done = NewEvaluationResult.objects.filter(user=user,
          item__task=self).count()
        
        _status.append('{0}/{1}'.format(_done, _items))
        
        # Compute average duration for this task and the given users
        _results = NewEvaluationResult.objects.filter(user=user, item__task=self)
        _durations = _results.values_list('duration', flat=True)
        
        _durations = [datetime_to_seconds(d) for d in _durations if d]
        _average_duration = reduce(lambda x, y: (x+y)/2.0, _durations, 0)
        
        _status.append('{:.2f} sec'.format(_average_duration))
        
        return _status
    
    def is_finished_for_user(self, user=None):
        """
        Returns True if this task is finished for the given user.
        """
        _items = EvaluationItem.objects.filter(task=self).count()
        _done = NewEvaluationResult.objects.filter(user=user,
          item__task=self).count()
        return _items == _done
    
    def get_finished_for_user(self, user=None):
        """
        Returns tuple (finished, total) number of items for the given user.
        """
        _items = EvaluationItem.objects.filter(task=self).count()
        _done = NewEvaluationResult.objects.filter(user=user,
          item__task=self).count()
        return (_done, _items)

    def export_to_xml(self):
        """
        Renders this EvaluationTask as XML String.
        """
        template = get_template('evaluation/result_task.xml')
        
        # pylint: disable-msg=E1101
        _task_type = self.get_task_type_display().lower().replace(' ', '-')
        
        # If a task_xml file is available, populate self.task_attributes.
        self.reload_dynamic_fields()
        
        _attr = self.task_attributes.items()
        attributes = ' '.join(['{}="{}"'.format(k, v) for k, v in _attr])
        
        results = []
        for item in EvaluationItem.objects.filter(task=self):
            for _result in item.evaluationresult_set.all():
                results.append(_result.export_to_xml())
        
        context = {'task_type': _task_type, 'attributes': attributes,
          'results': results}
        return template.render(Context(context))

class RankingTask(EvaluationTask):
    def generateItems(self, *args, **kwargs):
        documents = self.corpus.documents.all()
        for d in documents:
            sentences = corpusM.SourceSentence.objects.filter(document=d)
            for s in sentences:
                i = EvaluationItem(task=self, source_sentence=s)
                i.save()
                for system in self.systems.all():
                    i.systems.add(system)
                i.save()

class SelectAndPostEditTask(EvaluationTask):
    def generateItems(self, *args, **kwargs):
        documents = self.corpus.documents.all()
        for d in documents:
            sentences = corpusM.SourceSentence.objects.filter(document=d)
            for s in sentences:
                i = EvaluationItem(task=self, source_sentence=s)
                i.save()
                for system in self.systems.all():
                    i.systems.add(system)
                i.save()

class PostEditAllTask(EvaluationTask):
    def generateItems(self, *args, **kwargs):
        documents = self.corpus.documents.all()
        for d in documents:
            sentences = corpusM.SourceSentence.objects.filter(document=d)
            for system in self.systems.all():
                for s in sentences:
                    i = EvaluationItem(task=self, source_sentence=s)
                    i.save()
                    i.systems.add(system)
                    i.save()
                    
class QualityTask(EvaluationTask):
    def generateItems(self, *args, **kwargs):
        documents = self.corpus.documents.all()
        for d in documents:
            sentences = corpusM.SourceSentence.objects.filter(document=d)
            for system in self.systems.all():
                for s in sentences:
                    i = EvaluationItem(task=self, source_sentence=s)
                    i.save()
                    i.systems.add(system)
                    i.save()

class ErrorClassificationType(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __unicode__(self):
        return self.name

class ErrorClassificationTask(EvaluationTask):
    errorTypes = models.ManyToManyField(ErrorClassificationType)
    
    def generateItems(self, *args, **kwargs):
        documents = self.corpus.documents.all()
        for d in documents:
            sentences = corpusM.SourceSentence.objects.filter(document=d)
            for system in self.systems.all():
                for s in sentences:
                    i = EvaluationItem(task=self, source_sentence=s)
                    i.save()
                    i.systems.add(system)
                    i.save()

class EvaluationItem(models.Model):
    """
    Evaluation Item object model.
    """
    task = models.ForeignKey(
      EvaluationTask,
      db_index=True
    )
    
    source_sentence = models.ForeignKey(corpusM.SourceSentence)

    # We "repeat" the systems here, because depending of the task
    # type, it may be all of the task or only a subset (one?) of them
    # (e.g. post-edit-all)
    systems = models.ManyToManyField(corpusM.TranslationSystem)
    
    # These fields are derived from item_xml and NOT stored in the database.
    attributes = None
    source = None
    reference = None
    translations = None
    
    class Meta:
        """
        Metadata options for the EvaluationItem object model.
        """
        ordering = ('id',)
        verbose_name = "EvaluationItem object"
        verbose_name_plural = "EvaluationItem objects"
    
    def __init__(self, *args, **kwargs):
        """
        Makes sure that self.translations are available.
        """
        super(EvaluationItem, self).__init__(*args, **kwargs)
        try:
           self.reload_dynamic_fields()
        except:
           pass

    def __unicode__(self):
        """
        Returns a Unicode String for this EvaluationItem object.
        """
        return u'<evaluation-item id="{0}">'.format(self.id)

    def save(self, *args, **kwargs):
        """
        Makes sure that validation is run before saving an object instance.
        """
        # Enforce validation before saving EvaluationItem objects.
        self.full_clean()        
        
        super(EvaluationItem, self).save(*args, **kwargs)
    
    def reload_dynamic_fields(self):
        """
        Reloads source, reference, and translations from self.item_xml.
        """
        if self.id: # If it has been initialized
            self.reference = None

            self.source = (self.source_sentence.text,[])
            systems = self.systems.all()
            self.translations = []
            for s in systems:
                sourceDocument = self.source_sentence.document
                translatedDocument = corpusM.TranslatedDocument.objects.get(source=sourceDocument,
                                                                            translation_system=s,
                                                                            language=self.task.targetLanguage)
                translation = corpusM.Translation.objects.get(source_sentence=self.source_sentence,
                                                              document=translatedDocument)
                self.translations.append(translation)


class NewEvaluationResult(models.Model):
    """
    Evaluation Result object model.
    """
    item = models.ForeignKey(EvaluationItem, db_index=True, null=True)
    user = models.ForeignKey(User, db_index=True, null=True)
    duration = models.TimeField(blank=True, null=True, editable=False)
    skipped = models.BooleanField()

    class Meta:
        """
        Metadata options for the EvaluationResult object model.
        """
        ordering = ('id',)
        verbose_name = "NewEvaluationResult object"
        verbose_name_plural = "NewEvaluationResult objects"

    def readable_duration(self):
        """
        Returns a readable version of the this EvaluationResult's duration.
        """
        return '{}'.format(self.duration)

    def __unicode__(self):
        """
        Returns a Unicode String for this EvaluationResult object.
        """
        return u'<evaluation-result id="{0}">'.format(self.id)

class QualityResult(NewEvaluationResult):
    score = models.IntegerField()
    system = models.ForeignKey(corpusM.TranslationSystem, null=True)

class RankingResult(NewEvaluationResult):
    pass

class _RankingRank(models.Model):
    translation = models.ForeignKey(corpusM.Translation)
    rank = models.IntegerField()
    result = models.ForeignKey(RankingResult)
    
class PostEditAllResult(NewEvaluationResult):
    sentence = models.TextField(null=True)
    fromScratch = models.BooleanField()
    system = models.ForeignKey(corpusM.TranslationSystem, null=True)

class SelectAndPostEditResult(NewEvaluationResult):
    sentence = models.TextField(null=True)
    fromScratch = models.BooleanField()
    system = models.ForeignKey(corpusM.TranslationSystem, null=True)

class ErrorClassificationResult(NewEvaluationResult):
    tooManyErrors = models.BooleanField()
    missingWords = models.BooleanField()

class _ErrorClassificationEntry(models.Model):
    type = models.ForeignKey(ErrorClassificationType)
    isSevere = models.BooleanField()
    wordPosition = models.IntegerField()
    result = models.ForeignKey(ErrorClassificationResult)

class EvaluationResult(models.Model):
    """
    Evaluation Result object model.
    """
    item = models.ForeignKey(
      EvaluationItem,
      db_index=True
    )
    
    user = models.ForeignKey(
      User,
      db_index=True
    )
    
    duration = models.TimeField(blank=True, null=True, editable=False)
    
    def readable_duration(self):
        """
        Returns a readable version of the this EvaluationResult's duration.
        """
        return '{}'.format(self.duration)
    
    raw_result = models.TextField(editable=False, blank=False)
    
    results = None
    
    class Meta:
        """
        Metadata options for the EvaluationResult object model.
        """
        ordering = ('id',)
        verbose_name = "EvaluationResult object"
        verbose_name_plural = "EvaluationResult objects"
    
    def __init__(self, *args, **kwargs):
        """
        Makes sure that self.results are available.
        """
        super(EvaluationResult, self).__init__(*args, **kwargs)
        
        # If raw_result is available, populate dynamic field.
        self.reload_dynamic_fields()
    
    def __unicode__(self):
        """
        Returns a Unicode String for this EvaluationResult object.
        """
        return u'<evaluation-result id="{0}">'.format(self.id)
    
    def reload_dynamic_fields(self):
        """
        Reloads source, reference, and translations from self.item_xml.
        """
        if self.raw_result and self.raw_result != 'SKIPPED':
            _task_type = self.item.task.get_task_type_display()
            try:
                if _task_type == 'Quality Checking':
                    self.results = self.raw_result
                
                elif _task_type == 'Ranking':
                    self.results = self.raw_result.split(',')
                    self.results = [int(x) for x in self.results]
                
                elif _task_type == 'Post-editing':
                    self.results = self.raw_result.split('\n')
                
                elif _task_type == 'Error classification':
                    self.results = self.raw_result.split('\n')
                    self.results = [x.split('=') for x in self.results]
                
                elif _task_type == '3-Way Ranking':
                    self.results = self.raw_result
            
            # pylint: disable-msg=W0703
            except Exception, msg:
                self.results = msg
    
    def export_to_xml(self):
        """
        Renders this EvaluationResult as XML String.
        """
        _task_type = self.item.task.get_task_type_display()
        if _task_type == 'Quality Checking':
            return self.export_to_quality_checking_xml()
        
        elif _task_type == 'Ranking':
            return self.export_to_ranking_xml()
        
        elif _task_type == 'Post-editing':
            return self.export_to_postediting_xml()
        
        elif _task_type == 'Error classification':
            return self.export_to_error_classification_xml()
        
        elif _task_type == '3-Way Ranking':
            return self.export_to_three_way_ranking_xml()
    
    def export_to_quality_checking_xml(self):
        """
        Renders this EvaluationResult as Quality Checking XML String.
        """
        template = get_template('evaluation/result_quality_checking.xml')
        
        _attr = self.item.attributes.items()
        attributes = ' '.join(['{}="{}"'.format(k, v) for k, v in _attr])
        
        context = {
          'attributes': attributes,
          'duration': '{}'.format(self.duration),
          'result': self.results,
          'skipped': self.results is None,
          'user': self.user,
        }
        
        return template.render(Context(context))
    
    def export_to_ranking_xml(self):
        """
        Renders this EvaluationResult as Ranking XML String.
        """
        template = get_template('evaluation/result_ranking.xml')
        
        _attr = self.item.attributes.items()
        attributes = ' '.join(['{}="{}"'.format(k, v) for k, v in _attr])
        
        skipped = self.results is None
        
        translations = []
        if not skipped:
            for index, translation in enumerate(self.item.translations):
                _items = translation[1].items()
                _attr = ' '.join(['{}="{}"'.format(k, v) for k, v in _items])
                _rank = self.results[index]
                translations.append((_attr, _rank))
        
        context = {
          'attributes': attributes,
          'duration': '{}'.format(self.duration),
          'skipped': skipped,
          'translations': translations,
          'user': self.user,
        }
        
        return template.render(Context(context))
    
    def export_to_postediting_xml(self):
        """
        Renders this EvaluationResult as Post-editing XML String.
        """
        template = get_template('evaluation/result_postediting.xml')
        
        _attr = self.item.attributes.items()
        attributes = ' '.join(['{}="{}"'.format(k, v) for k, v in _attr])
        
        skipped = self.results is None
        
        if not skipped:
            from_scratch = self.results[0] == 'FROM_SCRATCH'
            if from_scratch:
                edit_id = self.results[1]
            else:
                edit_id = self.results[0]
            
            postedited = self.results[-1]
            
            _attr = self.item.translations[int(edit_id)][1].items()
        
        else:
            from_scratch = False
            edit_id = None
            postedited = ''
            _attr = []

        _export_attr = ' '.join(['{}="{}"'.format(k, v) for k, v in _attr])
        
        context = {
          'attributes': attributes,
          'duration': '{}'.format(self.duration),
          'edit_id': edit_id,
          'from_scratch': from_scratch,
          'postedited': postedited.encode('utf-8'),
          'skipped': skipped,
          'translation_attributes': _export_attr,
          'user': self.user,
        }
        
        return template.render(Context(context))
    
    def export_to_error_classification_xml(self):
        """
        Renders this EvaluationResult as Error Classification XML String.
        """
        template = get_template('evaluation/result_error_classification.xml')
        
        _attr = self.item.attributes.items()
        attributes = ' '.join(['{}="{}"'.format(k, v) for k, v in _attr])
        
        errors = []
        too_many_errors = False
        missing_words = False
        
        if self.results:
            for error in self.results:
                if len(error) == 2:
                    word_id = int(error[0])
                    for details in error[1].split(','):
                        error_class, severity = details.split(':')
                        errors.append((word_id, error_class, severity))
                
                elif error[0] == 'MISSING_WORDS':
                    missing_words = True
                
                elif error[0] == 'TOO_MANY_ERRORS':
                    too_many_errors = True
        
        # Sort by increasing word id.
        errors.sort()
        
        skipped = self.results is None
        
        context = {
          'attributes': attributes,
          'duration': '{}'.format(self.duration),
          'errors': errors,
          'missing_words': missing_words,
          'skipped': skipped,
          'too_many_errors': too_many_errors,
          'user': self.user,
        }
        
        return template.render(Context(context))
    
    def export_to_three_way_ranking_xml(self):
        """
        Renders this EvaluationResult as 3-Way Ranking XML String.
        """
        template = get_template('evaluation/result_three_way_ranking.xml')
        
        _attr = self.item.attributes.items()
        attributes = ' '.join(['{}="{}"'.format(k, v) for k, v in _attr])
        
        context = {
          'attributes': attributes,
          'duration': '{}'.format(self.duration),
          'result': self.results,
          'skipped': self.results is None,
          'user': self.user,
        }
        
        return template.render(Context(context))

