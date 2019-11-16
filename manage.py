from flask_script import Manager
from app import app

#manager = Manager(app)
#app.config['DEBUG'] = True # Ensure debugger will load.

if __name__ == '__main__':
  app.run()


