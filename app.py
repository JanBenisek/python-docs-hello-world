from flask import Flask
import os
app = Flask(__name__)

@app.route('/')
def hello_world():
    result = ('URL: {}, KEY: {}, FLASK_ENV: {}, '
              'FLASK_DEBUG: {}, FLASK_APP: {}').format(os.environ['URL'],
                                                       os.environ['KEY'],
                                                       os.environ['FLASK_ENV'],
                                                       os.environ['FLASK_DEBUG'],
                                                       os.environ['FLASK_APP'])
   
   return result

# Start App
if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000)
