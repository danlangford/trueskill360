# trueskill360

[![Build Status](https://travis-ci.org/danlangford/trueskill360.svg?branch=master)](https://travis-ci.org/danlangford/trueskill360)
[![Requirements Status](https://requires.io/github/danlangford/trueskill360/requirements.svg?branch=master)](https://requires.io/github/danlangford/trueskill360/requirements/?branch=master)
[![Code Issues](https://www.quantifiedcode.com/api/v1/project/28c6e47bac3740cf9bad933ea01b5d1a/badge.svg)](https://www.quantifiedcode.com/app/project/28c6e47bac3740cf9bad933ea01b5d1a)
[![Code Climate](https://codeclimate.com/github/danlangford/trueskill360/badges/gpa.svg)](https://codeclimate.com/github/danlangford/trueskill360)
[![Join the chat at https://gitter.im/danlangford/trueskill360](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/danlangford/trueskill360?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

a web service providing trueskill-style rankings



## Run Locally
1. Install the [App Engine Python SDK](https://developers.google.com/appengine/downloads).
See the README file for directions. You'll need python 2.7 and [pip 1.4 or later](http://www.pip-installer.org/en/latest/installing.html) installed too.

2. Clone this repo with

   ```
   git clone https://github.com/danlangford/trueskill360.git
   ```
3. Install dependencies in the project's lib directory.
   Note: App Engine can only import libraries from inside your project directory.

   ```
   cd trueskill360
   pip install -r requirements.txt -t lib
   ```
4. Run this project locally from the command line:

   ```
   dev_appserver.py .
   ```

Visit the application [http://localhost:8080](http://localhost:8080)

See [the development server documentation](https://developers.google.com/appengine/docs/python/tools/devserver)
for options when running dev_appserver.

## Deploy
To deploy the application:

1. Use the [Admin Console](https://appengine.google.com) to create a
   project/app id. (App id and project id are identical)
1. [Deploy the
   application](https://developers.google.com/appengine/docs/python/tools/uploadinganapp) with

   ```
   appcfg.py -A <your-project-id> --oauth2 update .
   ```
1. Congratulations!  Your application is now live at your-app-id.appspot.com

## Next Steps
This skeleton includes `TODO` markers to help you find basic areas you will want
to customize.

### Relational Databases and Datastore
To add persistence to your models, use
[NDB](https://developers.google.com/appengine/docs/python/ndb/) for
scale.  Consider
[CloudSQL](https://developers.google.com/appengine/docs/python/cloud-sql)
if you need a relational database.

### Installing Libraries
See the [Third party
libraries](https://developers.google.com/appengine/docs/python/tools/libraries27)
page for libraries that are already included in the SDK.  To include SDK
libraries, add them in your app.yaml file. Other than libraries included in
the SDK, only pure python libraries may be added to an App Engine project.

### Feedback
Star this repo if you found it useful. Use the github issue tracker to give
feedback on this repo.

## Contributing changes
See [CONTRIB.md](CONTRIB.md)

## Licensing
See [LICENSE](LICENSE)

## Author
Dan Langford
