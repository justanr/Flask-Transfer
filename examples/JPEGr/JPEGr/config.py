import os


class Config(object):
    DEBUG = True
    SECRET_KEY = "it's a secret to everybody"
    UPLOAD_PATH = 'pdf'

    @staticmethod
    def init_app(app):
        save_path = os.path.join(app.static_folder, Config.UPLOAD_PATH)
        if not os.path.exists(save_path):
            os.mkdir(save_path)
