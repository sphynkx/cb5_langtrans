#!/usr/bin/env python3
## Script for translation of web interface items in ClipBucket v5 using Google Translate service.
## (с) Sphynkx 2024

import re, sys, argparse, time, mysql.connector
from googletrans import Translator, LANGCODES

## Path to your ClipBucket installation. Modify this path for your case.
cb_path="/var/www/yurtube"


translator = Translator(service_urls=[
#    'translate.google.cn',
#    'translate.google.com.ru',
    'translate.google.com'
])
translator.raise_Exception = True


def checklangs(code='NONE'):
	'''
Without param prints list of available languages
With code as param checks for correctness of destination language and its code. 
	'''
	if code == "NONE": 
		print("Available languages and their codes:")
		for key, value, in enumerate(LANGCODES.items()):  print(f"{key}: {value[0].capitalize()}:   {value[1]}\t".expandtabs(40), end="\n"*(not key%4))
		print("\n")
	else:
		for key, value in LANGCODES.items():
			if value == code:
				return
	print("Lang is incorrect or unavailable. Run with `-s` option to see languages list\n")
	sys.exit(1)


## Instantiate the config parser
parser = argparse.ArgumentParser(
	formatter_class=argparse.RawDescriptionHelpFormatter, 
	description=f'''
	ClipBucket v5 LangTranslator..
	Script for translation of web interface items in ClipBucket v5 using Google Translate service. Common case:
	{sys.argv[0]} -l Russian -c ru output.sql
	''')
## Optional positional argument - for SQL file generation
parser.add_argument('sqlfile', type=str, nargs='?', help='Name for output SQL file')
## Optional argument - set/dont set both only. If set then perform request to DB and translation
parser.add_argument('-l', '--lang', type=str, help='Language name for translation')
parser.add_argument('-c', '--code', type=str, help='Language code for translation')
## Single options
parser.add_argument('-s', '--showlangs', help='Show avaulable languages and their codes', action="store_true")
parser.add_argument('-n', '--nodb',  help='Do not send to DB. Without -n and sql-filename the sql outputs to screen.', action="store_true")

## Analise input params. Without params gets help and quit
args = parser.parse_args(sys.argv[1:])
if len(sys.argv) < 2:
    parser.print_help()
    sys.exit(1)
if args.lang and not args.code:
	print("Parameters mismatch: if the `lang` is set then `code` also need to be set. Run with `-s` for available languages list\n")
	parser.print_help()
	sys.exit(1)
if args.showlangs:
	checklangs()
checklangs(args.code)


## Parse ClipBucket config
dbhost, dbname, dbprefix, dbuser, dbpass, dbport = 0, 0, 0, 0, 0, 0
f = open(f"{cb_path}/includes/config.php", "r")
for x in f:
    m = re.search(r'\$DBHOST.*?\'(.*?)\';', x)
    if m: dbhost=m[1]

    m = re.search(r'\$DBNAME.*?\'(.*?)\';', x)
    if m: dbname=m[1]

    m = re.search(r'\$DBUSER.*?\'(.*?)\';', x)
    if m: dbuser=m[1]

    m = re.search(r'\$DBPASS.*?\'(.*?)\';', x)
    if m: dbpass=m[1]

    m = re.search(r'\$DBPORT.*?\'(.*?)\';', x)
    if m: dbport=m[1]

    m = re.search(r'.*PREFIX.*\'(.*?)\'\);', x)
    if m: dbprefix=m[1]

config = {
  'user': dbuser,
  'password': dbpass,
  'host': dbhost,
  'port': dbport,
  'database': dbname,
  'raise_on_warnings': True
}
db = mysql.connector.connect(**config)



def sql_lang_select(cmd):
	'''
	Read-requests to DB
	'''
	if db and db.is_connected():
		with db.cursor() as cursor:
			result = cursor.execute(cmd)
			rows = cursor.fetchall()
##            for row in rows:
##                print(row)
##		db.close()
		return rows
	else:
		print("Could not connect")



def sql_lang_insert(lng, langmax):
	'''
Write-requests to DB.
If something went wrong you could delete added lang:
SELECT * from cb_languages;
and then:
DELETE from cb_languages_translations WHERE language_id=5;
DELETE from cb_languages WHERE language_id=5;
or:
DELETE from cb_languages_translations WHERE language_id=(SELECT MAX(language_id) from cb_languages);
DELETE from cb_languages WHERE language_id=(SELECT MAX(language_id) from cb_languages);
	'''
	arr=[(a,b) for a,b in lng]
	if db and db.is_connected():
		with db.cursor() as cursor:
			cursor.execute(f"INSERT INTO {dbprefix}languages (language_id, language_name, language_code, language_active, language_default) VALUES({langmax}, '{args.lang}', '{args.code}','yes','no')")
			cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
			cursor.executemany(f"INSERT IGNORE INTO {dbprefix}languages_translations (language_id, id_language_key, translation) VALUES({langmax}, %s, %s)", arr)
		db.commit()



def translate(arr, langcode):
    '''
Take source array of items to translate in format [ [a,b], [c,d], [e,f], ...] 
Transpose to [[a,c,e, ...], [b,d,f, ...] ]
Split to chunks, translate chunks, join chunks back, transpose back to initial format, and return it
GoogleTrans has some limitation and bug: limit on request size is 5kb, batch translation (for array) is broken - need send as string
Also GoogleTrans could silently pass some phrases in chunks, and returned chunk appears shorter than initial
Other limitation - 50000 requests per day. If script fails and return error 429 - try later.
NB: GoogleTranslator translates the more than need. Namely it also translates content of HTML tags and CSS params. Clipbucket may work buggy when switch to added lang.
Need to check all added translations manually.
For example, id_language_key 431  may have broken CSS params. This breaks videos thumbs on start page
Also 452 need change from `%s %` to `%s %s`
    '''
    arr2 = zip(*arr)
    arr = []
    arr = [list(i) for i in arr2]
    ids = arr[0] ## Save id subarray

    arr2 = []
    rangesize = 1 ## Chunk size 100 works fast but may pass some phrases. Chunk size 1 works slow but stable
    for i in range(0, len(arr[1]), rangesize):
        strchunk = " ^^^ ".join(arr[1][i:i+rangesize]) ## chunks to strings
##        strchunk = strchunk.upper() ## Translator surrogate - for debug purposes
        strchunk = translator.translate(strchunk, dest=langcode).text
        time.sleep(0.5)
        strchunk=strchunk.replace("%S", "%s") ## some fix after translation
        strchunk=strchunk.replace("'", "\'\'")
        print(f"STR_CHUNK({i}): {strchunk}") ## translated string
        arr2 += strchunk.split(" ^^^ ") 
## Combain back ids and translated items in finally transposed state
    arr = [[ids[i], arr2[i]] for i in range(len(ids))]
    return arr



def main():
	## Get next lang ID that need to insert befor translation insertion
	langmax = sql_lang_select(f"SELECT MAX(language_id) FROM {dbprefix}languages")[0][0] + 1
	## Get items to translate
	items = sql_lang_select(f"SELECT id_language_key,translation FROM {dbprefix}languages_translations WHERE language_id=1")

	arr = []
	lng = []
	## Items to translate. Get array of arrays [ [id_language_key, translation], ... ] 1119 arrays in array
	for item in items: arr.append(list(item))

	if args.lang and args.code: arr = translate(arr, args.code)

## make orig text for put in sql as comments
	tempitm = zip(*items)
	itm = []
	itm = [list(i) for i in tempitm]

## Here is insertion of translations for SQL-file:
	for a,i in zip(arr, itm[1]): lng.append(f"INSERT IGNORE INTO {dbprefix}languages_translations (language_id, id_language_key, translation) VALUES({langmax}, {a[0]}, \'{a[1]}\'); \t/*'{i}'*/")

## Store to SQL-file:
	if args.sqlfile:
		s = open(args.sqlfile, "w")
		s.write(f"INSERT IGNORE INTO {dbprefix}languages (language_id, language_name, language_code, language_active, language_default) VALUES({langmax}, '{args.lang}', '{args.code}','yes','no'); /* Set new language*/\n\n")
		s.write("\n".join(lng))
		s.close

## If args are only -l and -c - print sql-commands on screen
	if not args.sqlfile and not args.nodb:
		for l in lng: print(l)

	if not args.nodb:
		sql_lang_insert(arr, langmax)

	db.close()



if __name__ == '__main__':
	main()
