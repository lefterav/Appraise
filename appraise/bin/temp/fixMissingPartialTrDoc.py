import sys
import corpus.models as models

if len(sys.argv)<2:
    print "This script has been written to face cases were the entire source sentence document was uploaded, but only part of the target sentences document. This breaks ranking tasks, because they require all 3 systems available. \n\n USE: \nAppend the stem of the source document id that you want to check. \nAdd a second parameter '--process' if you want to fix the error. \n\n*May only work for naming conventions of TaraXU R4 so modifications may be needed for any other use"
else:    
    filename_stem = sys.argv[1]

#add this as a second parameter, otherwise only info will be displayed, with not correction
try:
    process = (sys.argv[2]=="--process")
except:
    process = False 
path = '/wizard/appraise/data/r4/euroscript/'

source_document = models.SourceDocument.objects.get(custom_id='{}.src'.format(filename_stem))

t_documents = models.TranslatedDocument.objects.filter(source=source_document)

#len(models.Translation.objects.filter(document=t_moses))
source_sentences = models.SourceSentence.objects.filter(document=source_document)

#filename = '/wizard/appraise/data/r4/euroscript/customer0_new_en-de.trados'




for t_document in t_documents:
  #get sentences for translated document
  t_sentences = models.Translation.objects.filter(document=t_document)
  #remove part of system name after hyphen
  system_name = t_document.translation_system.name.split('-')[0]

  #this is the last sentence uploaded for the particular system
  last_entry = len(t_sentences)
  
  #check if translated sentences are less than expected
  if last_entry < len(source_sentences):
    print "[{}] unsuccessful uploading of {}: {} < {}".format(filename_stem, system_name, last_entry, len(source_sentences))
    #act only if required by user
    if process:
      #fetch file based on given filename pattern and read lines
      filename = '{}/{}.{}'.format(path, filename_stem, system_name)
      file_lines = open(filename).readlines()

      #iterate only in the part of the file and the source sentences that have not been uploaded
      for s_sentence, t_sentence_text in zip(source_sentences[last_entry:], file_lines[last_entry:]):
        
        translation = models.Translation(source_sentence=s_sentence, text=t_sentence_text, document=t_document)
        translation.save()
