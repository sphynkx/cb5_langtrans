This script generates new translations for elements of UI in [ClipBucket v5](https://github.com/MacWarrior/clipbucket-v5) installation.
Script uses common [GoogleTranslate](https://cloud.google.com/translate) service, python module [googletrans](https://pypi.org/project/googletrans/), and need to recheck and fix some translations manually.

Script allows to add new localisation in the database directly or generate separate SQL file.

Script didn't test under Windows. Incompatible with old ClipBucket versions.

## Setup

Setup additional modules:
```
pip install -r requirements.txt
```
Modify path according to your ClipBucket-v5 installation: edit value of `cb_path` (line 9).


## Usage

Just run the script and it will show help.

Example of common usage:
```
./cb5_langtrans.py -l Russian -c ru output.sql
```
If the destination language options `-l` and `-c` are set then will perform translation. Both options required. List of available languages and their codes - see with `-s`.
If set filename then the script also generates SQL-file, which could be edit and then push to DB manually. Or insert all translations into DB directly. Or print SQL commands to screen.

After finish script run new language set as active and not default. With new language would be work some buggy. So need to recheck and fix all translated items.


## Issues, bugs, limitations

There is some [limitations on usage Google API](https://developers.google.com/analytics/devguides/reporting/mcf/v3/limits-quotas):

* 50000 requests per day.
* 10 requests per second.
* Max text size to translation is 5kb.
* In some cases of multiline string GoogleTranslate may loose and pass some lines.

If limit exceeded the script will be blocked and will return error 429. In this case need to retry to run it next day.

Google service may overload and cause timeout. In this case rerun script again. Write to DB goes after correct finish of translation process.

GoogleTranslator translates the more than need. Namely it also translates content of HTML tags and CSS params, breaks quotes and symbols register. Clipbucket may work buggy when switch to added lang.

Need to check all added translations manually. For example there was case that video's thumbs are not show on start page. Cause was broken format in items with `id_language_key` 431 and 452.

Seems the language edit service in ClipBucket-v5 is some buggy for now (editions aren't apply to database). Better to edit translations in database directly (for example via PHPMyAdmin).


## Useful commands
For development purposes would be better to use the separate copy of actual ClipBucket database. At first need to create new database:
```
mysql -uroot -p
```
and:
```
CREATE DATABASE clipbucket5dev;
GRANT ALL PRIVILEGES ON clipbucket5dev.* TO 'clipbucket'@'localhost';
FLUSH PRIVILEGES;
```
Next get backup of actual database and load it to this copy:
```
mysqldump -uroot -p clipbucket5 > clipbucket5_backup.sql
mysql -uroot -p clipbucket5dev < clipbucket5_backup.sql
```
To check is everything OK modify your `/var/www/clipbucket/includes/config.php` - change database name to that `clipbucket5dev`. Alternatively you may add line `dbname = clipbucket5dev` before declaration of `config` (line 91).

If something went wrong.. You may remove added language - find its `language_id` in `cb_languages` table:
```
SELECT language_id,language_name FROM cb_languages;
```
Remove it. Also in `cb_languages_translations` table remove all items that are linked to this language (assume `language_id` is 5):
```
DELETE from cb_languages_translations WHERE language_id=5;
DELETE from cb_languages WHERE language_id=5;
```
or just so:
```
DELETE from cb_languages_translations WHERE language_id=(SELECT MAX(language_id) FROM cb_languages);
DELETE from cb_languages WHERE language_id=(SELECT MAX(language_id) FROM cb_languages);
```
