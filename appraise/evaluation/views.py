# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@dfki.de>
"""
import logging

from datetime import datetime
from random import randint, seed, shuffle
from time import mktime

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.template import RequestContext

from evaluation.models import APPRAISE_TASK_TYPE_CHOICES, \
  EvaluationTask, EvaluationItem, EvaluationResult, NewEvaluationResult, \
  RankingResult, _RankingRank, \
  SelectAndPostEditResult, PostEditAllResult, \
  ErrorClassificationResult, _ErrorClassificationEntry, ErrorClassificationType
from appraise.settings import LOG_LEVEL, LOG_HANDLER, COMMIT_TAG

import corpus.models as corpusM

# Setup logging support.
logging.basicConfig(level=LOG_LEVEL)
LOGGER = logging.getLogger('evaluation.views')
LOGGER.addHandler(LOG_HANDLER)


ERROR_CLASSES = ["terminology", "lexical choice", "syntax", "insertion",
  "morphology", "misspelling", "punctuation", "other"]
#ERROR_CLASSES = ["aaa", "bbb", "ccc"];


def _save_results(item, user, duration, raw_result):
    """
    Creates or updates the EvaluationResult for the given item and user.
    """
    LOGGER.debug('item: {}, user: {}, duration: {}, raw_result: {}'.format(
      item, user, duration, raw_result.encode('utf-8')))
    
    _existing_result = EvaluationResult.objects.filter(item=item, user=user)
    
    if _existing_result:
        _result = _existing_result[0]
    
    else:
        _result = EvaluationResult(item=item, user=user)
    
    _result.duration = duration
    _result.raw_result = raw_result
    _result.save()


def _find_next_item_to_process(items, user, random_order=False):
    """
    Computes the next item the current user should process or None, if done.
    """
    user_results = NewEvaluationResult.objects.filter(user=user)
    
    processed_items = user_results.values_list('item__pk', flat=True)
    
    # cfedermann: this might be sub optimal wrt. performance!
    #unprocessed_items = list(items.exclude(pk__in=processed_items))
    #
    #if random_order:
    #    shuffle(unprocessed_items)
    #
    #if unprocessed_items:
    #    return unprocessed_items[0]
    unprocessed_items = items.exclude(pk__in=processed_items)
    if unprocessed_items:
        return unprocessed_items[0]
    else: 
        return None


def _compute_context_for_item(item):
    """
    Computes the source and reference texts for item, including context.
    """
    source_text = [None, None, None]
    reference_text = [None, None, None]
    
    context_length = item.task.context_length
    sourceSentenceId = item.source_sentence.id
    sourceDocument = item.source_sentence.document
    leftContext = []
    for i in range(1, context_length+1):
        try:
            leftContext.append(corpusM.SourceSentence.objects.get(document=sourceDocument, id=sourceSentenceId-i).text)
        except corpusM.SourceSentence.DoesNotExist:
            break
    leftContext.reverse()
    source_text[0] = " ".join(leftContext)

    source_text[1] = item.source[0]

    rightContext = []
    for i in range(1, context_length+1):
        try:
            rightContext.append(corpusM.SourceSentence.objects.get(document=sourceDocument, id=sourceSentenceId+i).text)
        except corpusM.SourceSentence.DoesNotExist:
            break
    source_text[2] = " ".join(rightContext)
    
    return (source_text, reference_text)


@login_required
def _handle_quality_checking(request, task, items):
    """
    Handler for Quality Checking tasks.
    
    Finds the next item belonging to the given task, renders the page template
    and creates an EvaluationResult instance on HTTP POST submission.
    
    """
    start_datetime = datetime.now()
    form_valid = False
    
    # If the request has been submitted via HTTP POST, extract data from it.
    if request.method == "POST":
        item_id = request.POST.get('item_id', None)
        now_timestamp = request.POST.get('now', None)
        submit_button = request.POST.get('submit_button', None)
        
        # The form is only valid if all variables could be found.
        form_valid = all((item_id, now_timestamp, submit_button))
    
    # If the form is valid, we have to save the results to the database.
    if form_valid:
        # Retrieve EvalutionItem instance for the given id or raise Http404.
        current_item = get_object_or_404(EvaluationItem, pk=int(item_id))
        
        # Compute duration for this item.
        now_datetime = datetime.fromtimestamp(float(now_timestamp))
        duration = start_datetime - now_datetime
        
        # If "Flag Error" was clicked, _raw_result is set to "SKIPPED".
        if submit_button == 'FLAG_ERROR':
            _raw_result = 'SKIPPED'
        
        # Otherwise, for quality checking, we just pass through the value.
        else:
            _raw_result = submit_button
        
        # Save results for this item to the Django database.
        _save_results(current_item, request.user, duration, _raw_result)
    
    # Find next item the current user should process or return to overview.
    item = _find_next_item_to_process(items, request.user)
    if not item:
        return redirect('evaluation.views.overview')
    
    # Compute source and reference texts including context where possible.
    source_text, reference_text = _compute_context_for_item(item)
    
    # Retrieve the number of finished items for this user and the total number
    # of items for this task. We increase finished_items by one as we are
    # processing the first unfinished item.
    finished_items, total_items = task.get_finished_for_user(request.user)
    finished_items += 1
    
    dictionary = {
      'action_url': request.path,
      'commit_tag': COMMIT_TAG,
      'description': task.description,
      'item_id': item.id,
      'now': mktime(datetime.now().timetuple()),
      'reference_text': reference_text,
      'source_text': source_text,
      'task_progress': '{0:03d}/{1:03d}'.format(finished_items, total_items),
      'title': 'Translation Quality Checking',
      'translation': item.translations[0].text,
    }
    
    return render(request, 'evaluation/quality_checking.html', dictionary)


@login_required
def _handle_ranking(request, task, items):
    """
    Handler for Ranking tasks.
    
    Finds the next item belonging to the given task, renders the page template
    and creates an EvaluationResult instance on HTTP POST submission.
    
    """
    form_valid = False
    
    # If the request has been submitted via HTTP POST, extract data from it.
    if request.method == "POST":
        item_id = request.POST.get('item_id', None)
        end_timestamp = request.POST.get('end_timestamp', None)
        order_random = request.POST.get('order', None)
        start_timestamp = request.POST.get('start_timestamp', None)
        submit_button = request.POST.get('submit_button', None)
        
        # The form is only valid if all variables could be found.
        form_valid = all((item_id, end_timestamp, order_random,
          start_timestamp, submit_button))
    
    # If the form is valid, we have to save the results to the database.
    if form_valid:
        # Retrieve EvalutionItem instance for the given id or raise Http404.
        current_item = get_object_or_404(EvaluationItem, pk=int(item_id))
        
        # Compute duration for this item.
        start_datetime = datetime.fromtimestamp(float(start_timestamp))
        end_datetime = datetime.fromtimestamp(float(end_timestamp))
        duration = end_datetime - start_datetime
        
        # Initialise order from order_random.
        order = [int(x) for x in order_random.split(',')]
        
        # Compute ranks for translation alternatives using order.
        ranks = {}
        for index in range(len(current_item.translations)):
            rank = request.POST.get('rank_{0}'.format(index), -1)
            ranks[order[index]] = int(rank)

        result = RankingResult(item=current_item, user=request.user, duration=duration)
        result.save() # get an object id
        
        # If "Flag Error" was clicked, _raw_result is set to "SKIPPED".
        if submit_button == 'FLAG_ERROR':
            _raw_result = 'SKIPPED'
            result.skipped = True
        
        # Otherwise, the _raw_result is a comma-separated list of ranks.
        elif submit_button == 'SUBMIT':
            _raw_result = range(len(current_item.translations))
            _raw_result = ','.join([str(ranks[x]) for x in _raw_result])
            
            #for (i, t) in enumerate(current_item.translations):
            #    print t.translation_system.name
                

            systems = current_item.task.systems.all()
            for (n, t) in enumerate(current_item.translations):
                rank = _RankingRank(translation=t, rank=ranks[n], result=result)
                rank.save()

        result.save()
    
    # Find next item the current user should process or return to overview.
    item = _find_next_item_to_process(items, request.user, task.random_order)
    if not item:
        return redirect('evaluation.views.overview')

    # Compute source and reference texts including context where possible.
    source_text, reference_text = _compute_context_for_item(item)
    
    # Retrieve the number of finished items for this user and the total number
    # of items for this task. We increase finished_items by one as we are
    # processing the first unfinished item.
    finished_items, total_items = task.get_finished_for_user(request.user)
    finished_items += 1
    
    # Create list of translation alternatives in randomised order.
    translations = []
    order = range(len(item.translations))
    shuffle(order)
    for index in order:
        translations.append((item.translations[index].text,))
    
    dictionary = {
      'action_url': request.path,
      'commit_tag': COMMIT_TAG,
      'description': task.description,
      'item_id': item.id,
      'order': ','.join([str(x) for x in order]),
      'reference_text': reference_text,
      'source_text': source_text,
      'task_progress': '{0:03d}/{1:03d}'.format(finished_items, total_items),
      'title': 'Ranking',
      'translations': translations,
    }
    
    return render(request, 'evaluation/ranking.html', dictionary)


@login_required
def _handle_postediting(request, task, items):
    """
    Handler for Post-editing tasks.
    
    Finds the next item belonging to the given task, renders the page template
    and creates an EvaluationResult instance on HTTP POST submission.
    
    """
    if request.method == "POST":
        item_id = request.POST.get('item_id')
        edit_id = request.POST.get('edit_id', 0)
        end_timestamp = request.POST.get('end_timestamp', None)
        submit_button = request.POST.get('submit_button')
        from_scratch = request.POST.get('from_scratch')
        postedited = request.POST.get('postedited', 'EMPTY')
        start_timestamp = request.POST.get('start_timestamp', None)
        
        current_item = get_object_or_404(EvaluationItem, pk=int(item_id))
        
        # Compute duration for this item.
        duration = None
        if end_timestamp and start_timestamp:
            start_datetime = datetime.fromtimestamp(float(start_timestamp))
            end_datetime = datetime.fromtimestamp(float(end_timestamp))
            duration = end_datetime - start_datetime
        
        print
        print "item_id: {0}".format(item_id)
        print "edit_id: {0}".format(edit_id)
        print "submit_button: {0}".format(submit_button)
        print "from_scratch: {0}".format(from_scratch)
        print "postedited: {0}".format(postedited.encode('utf-8'))
        print
        print request.POST
        print
        
        if current_item.task.task_type == "6":
            result = PostEditAllResult(item=current_item, user=request.user, duration=duration)
        else:
            result = SelectAndPostEditResult(item=current_item, user=request.user, duration=duration)
        if submit_button == 'SUBMIT':
            if from_scratch:
                result.fromScratch = True
            result.sentence = postedited.encode("utf-8")
            translation = current_item.translations[int(edit_id)]
            translatedDocument = corpusM.TranslatedDocument.objects.get(id=translation.document.id)
            result.system = translatedDocument.translation_system
            # Could we get here the system from the systems? Probably not...
            
            _results = []
            if from_scratch:
                _results.append('FROM_SCRATCH')
            
            _results.append(edit_id)
            _results.append(postedited)
            _raw_result = '\n'.join(_results)
            print _raw_result
        
        elif submit_button == 'FLAG_ERROR':
            result.skipped = True
        
        result.save()
    
    item = _find_next_item_to_process(items, request.user)
    if not item:
        return redirect('evaluation.views.overview')
    
    source_text, reference_text = _compute_context_for_item(item)
    _finished, _total = task.get_finished_for_user(request.user)
    
    dictionary = {'title': 'Post-editing', 'item_id': item.id,
      'source_text': source_text, 'reference_text': reference_text,
      'translations': [(t.text,) for t in item.translations],
      'description': task.description,
      'task_progress': '{0:03d}/{1:03d}'.format(_finished+1, _total),
      'action_url': request.path, 'commit_tag': COMMIT_TAG}
    
    return render(request, 'evaluation/postediting.html', dictionary)


@login_required
def _handle_error_classification(request, taskIn, items):
    """
    Handler for Error Classification tasks.
    
    Finds the next item belonging to the given task, renders the page template
    and creates an EvaluationResult instance on HTTP POST submission.
    
    """
    task = taskIn.errorclassificationtask
    if request.method == "POST":
        # downcast the task to the concrete type
        end_timestamp = request.POST.get('start_timestamp', None)
        item_id = request.POST.get('item_id')
        words = request.POST.get('words')
        missing_words = request.POST.get('missing_words')
        too_many_errors = request.POST.get('too_many_errors')
        start_timestamp = request.POST.get('start_timestamp', None)
        submit_button = request.POST.get('submit_button')
        
        current_item = get_object_or_404(EvaluationItem, pk=int(item_id))
        
        # Compute duration for this item.
        duration = None
        if end_timestamp and start_timestamp:
            start_datetime = datetime.fromtimestamp(float(start_timestamp))
            end_datetime = datetime.fromtimestamp(float(end_timestamp))
            duration = end_datetime - start_datetime
        
        errors = {}
        if words:
            for index in range(int(words)):
                _errors = {}
                taskErrors = [str(e.name) for e in task.errorTypes.all()]
                for error in taskErrors:
                    severity = request.POST.get('{0}_{1}'.format(error, index))
                    if severity and severity != "NONE":
                        _errors[error] = severity
                if _errors:
                    errors[index] = _errors
        
        print
        print "item_id: {0}".format(item_id)
        print "missing_words: {0}".format(missing_words)
        print "too_many_errors: {0}".format(too_many_errors)
        print "submit_button: {0}".format(submit_button)
        print "errors: {0}".format(errors)
        print
        
        result = ErrorClassificationResult(item=current_item, user=request.user, duration=duration,
                                           missingWords=(missing_words!=None),
                                           tooManyErrors=(too_many_errors!=None))
        result.save()
        if submit_button == 'SUBMIT':
            
            if not too_many_errors:
                for (wordIndex, wordErrors) in errors.items():
                    for (e, severity) in wordErrors.items():
                        errorType = ErrorClassificationType.objects.get(name=e)
                        isSevere = (severity == "SEVERE")
                        entry = _ErrorClassificationEntry(type=errorType, isSevere=isSevere,
                                                          wordPosition=wordIndex, result = result)
                        entry.save()
            
        elif submit_button == 'FLAG_ERROR':
            result.skipped = True
            result.save()
    
    item = _find_next_item_to_process(items, request.user)
    if not item:
        return redirect('evaluation.views.overview')
    
    source_text, reference_text = _compute_context_for_item(item)
    _finished, _total = task.get_finished_for_user(request.user)
    
    translation = item.translations[0].text
    words = translation.split(' ')
    dictionary = {'title': 'Error Classification', 'item_id': item.id,
      'source_text': source_text, 'reference_text': reference_text,
      'translation': translation,
      'words': words,
      'description': task.description,
      'error_classes': [str(e.name) for e in task.errorTypes.all()],
      'task_progress': '{0:03d}/{1:03d}'.format(_finished+1, _total),
      'action_url': request.path, 'commit_tag': COMMIT_TAG}
    
    return render(request, 'evaluation/error_classification.html', dictionary)


def _handle_three_way_ranking(request, task, items):
    """
    Handler for 3-Way Ranking tasks.

    Finds the next item belonging to the given task, renders the page template
    and creates an EvaluationResult instance on HTTP POST submission.

    """
    start_datetime = datetime.now()
    form_valid = False

    # If the request has been submitted via HTTP POST, extract data from it.
    if request.method == "POST":
        item_id = request.POST.get('item_id', None)
        now_timestamp = request.POST.get('now', None)
        order_reversed = request.POST.get('order_reversed', None)
        submit_button = request.POST.get('submit_button', None)

        # The form is only valid if all variables could be found.
        form_valid = all((item_id, now_timestamp, order_reversed,
          submit_button))

    # If the form is valid, we have to save the results to the database.
    if form_valid:
        # Retrieve EvalutionItem instance for the given id or raise Http404.
        current_item = get_object_or_404(EvaluationItem, pk=int(item_id))

        # Compute duration for this item.
        now_datetime = datetime.fromtimestamp(float(now_timestamp))
        duration = start_datetime - now_datetime

        # If "Flag Error" was clicked, _raw_result is set to "SKIPPED".
        if submit_button == 'FLAG_ERROR':
            _raw_result = 'SKIPPED'

        # Otherwise, for quality checking, we just pass through the value.
        # However, if the order had been reversed when rendering this form,
        # we have to invert the outcoming result here.
        else:
            _raw_result = submit_button
            
            if order_reversed == 'yes':
                if submit_button == 'A>B':
                    _raw_result = 'A<B'
                
                elif submit_button == 'A<B':
                    _raw_result = 'A>B'

        # Save results for this item to the Django database.
        _save_results(current_item, request.user, duration, _raw_result)

    # Find next item the current user should process or return to overview.
    item = _find_next_item_to_process(items, request.user)
    if not item:
        return redirect('evaluation.views.overview')

    # Compute source and reference texts including context where possible.
    source_text, reference_text = _compute_context_for_item(item)
    
    # Replace [[[markup]]] with proper HTML markup in the current sentence
    # only.  To avoid confusion, we delete the [[[markup]]] from the context.
    if source_text[0]:
        source_text[0] = source_text[0].replace('[[[', '').replace(']]]', '')
    
    source_text[1] = source_text[1].replace('[[[', '<code>')
    source_text[1] = source_text[1].replace(']]]', '</code>')
    
    if source_text[2]:
        source_text[2] = source_text[2].replace('[[[', '').replace(']]]', '')

    # Retrieve the number of finished items for this user and the total number
    # of items for this task. We increase finished_items by one as we are
    # processing the first unfinished item.
    finished_items, total_items = task.get_finished_for_user(request.user)
    finished_items += 1

    # Create list of translation alternatives in randomised order.  For 3-Way
    # Ranking tasks, we only use the first two translations which may come in
    # random order.  If so, order_reversed is set to True to allow us to later
    # create proper EvaluationResult instances.
    translations = item.translations[:2]
    order_reversed = False
    if randint(0, 1):
        translations.reverse()
        order_reversed = True

    dictionary = {
      'action_url': request.path,
      'commit_tag': COMMIT_TAG,
      'description': task.description,
      'item_id': item.id,
      'now': mktime(datetime.now().timetuple()),
      'order_reversed': order_reversed,
      'reference_text': reference_text,
      'source_text': source_text,
      'task_progress': '{0:03d}/{1:03d}'.format(finished_items, total_items),
      'title': '3-Way Ranking',
      'translations': translations,
    }
    
    return render(request, 'evaluation/three_way_ranking.html', dictionary)


@login_required
def task_handler(request, task_id):
    """
    General task handler.
    
    Finds the task with the given task_id and redirects to its task handler.
    
    """
    LOGGER.info('Rendering task handler view for user "{0}".'.format(
      request.user.username or "Anonymous"))
    
    task = get_object_or_404(EvaluationTask, task_id=task_id)
    items = EvaluationItem.objects.filter(task=task)
    if not items:
        return redirect('evaluation.views.overview')
    
    _task_type = task.get_task_type_display()
    if _task_type == 'Quality Checking':
        return _handle_quality_checking(request, task, items)
    
    elif _task_type == 'Ranking':
        return _handle_ranking(request, task, items)
    
    elif _task_type == 'Select-and-post-edit':
        return _handle_postediting(request, task, items)
    
    elif _task_type == 'Error classification':
        return _handle_error_classification(request, task, items)
    
    elif _task_type == '3-Way Ranking':
        return _handle_three_way_ranking(request, task, items)

    elif _task_type == 'Post-edit-all':
        return _handle_postediting(request, task, items)

    
    _msg = 'No handler for task type: "{0}"'.format(_task_type)
    raise NotImplementedError, _msg


@login_required
def overview(request):
    """
    Renders the evaluation tasks overview.
    """
    LOGGER.info('Rendering evaluation task overview for user "{0}".'.format(
      request.user.username or "Anonymous"))
    
    # Re-initialise random number generator.
    seed(None)
    
    evaluation_tasks = {}
    for task_type_id, task_type in APPRAISE_TASK_TYPE_CHOICES:
        # We collect a list of task descriptions for this task_type.
        evaluation_tasks[task_type] = []
        
        # Super users see all EvaluationTask items, even non-active ones.
        if request.user.is_superuser:
            _tasks = EvaluationTask.objects.filter(task_type=task_type_id)
        
        else:
            _tasks = EvaluationTask.objects.filter(task_type=task_type_id,
              users=request.user, active=True)
        
        # Loop over the QuerySet and compute task description data.
        for _task in _tasks:
            _task_data = {
              'finished': _task.is_finished_for_user(request.user),
              'header': _task.get_status_header,
              'status': _task.get_status_for_user(request.user),
              'task_name': _task.task_name,
              'url': _task.get_absolute_url(),
            }
            
            # Append new task description to current task_type list.
            evaluation_tasks[task_type].append(_task_data)
        
        # If there are no tasks descriptions for this task_type, we skip it.
        if len(evaluation_tasks[task_type]) == 0:
            evaluation_tasks.pop(task_type)
    
    dictionary = {
      'commit_tag': COMMIT_TAG,
      'evaluation_tasks': evaluation_tasks,
      'title': 'Evaluation Task Overview',
    }
    
    return render(request, 'evaluation/overview.html', dictionary)
