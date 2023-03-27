import uuid
import os
from flask import Flask
from flask import send_file
from flask import abort
from flask import request
from flask.views import MethodView
from flask import jsonify
from celery import Celery
from celery.result import AsyncResult
from upscale.upscale import upscale



app_name = 'upscale_image'
app = Flask(app_name)

app.config['UPLOAD_FOLDER'] = 'files'

# перед началом запускаем celery командaми: "celery -A main.celery" , "celery -A main.celery worker"

# По умолчанию у redis есть несколько БД (используем 1 и 2)
# broker - через что берем задачи на celery, backend - куда складываем резульаты работы celery
celery = Celery(
    app_name,
    backend='redis://localhost:6379/1',
    broker='redis://localhost:6379/2'
)
celery.conf.update(app.config)

class ContextTask(celery.Task):
    def __call__(self, *args, **kwargs):
        with app.app_context():
            return self.run(*args, **kwargs)
celery.Task = ContextTask


# обозначаем что эта ф-кция может исполняться внутри celery
@celery.task()
def upscale_image(image_path):
    base, extension = image_path.split('.')
    out_path = f'{base}-up.{extension}'
    result = upscale(image_path, out_path)
    return result


class Upscale(MethodView):
    def post(self):
        image_path = self.save_image('image')
        task = upscale_image.delay(image_path)
        return jsonify(
            {'task_id': task.id}
        )

    def save_image(self, file):
        image = request.files.get(file)
        extension = image.filename.split('.')[-1]
        path = os.path.join('files', f'{uuid.uuid4()}.{extension}')
        image.save(path)
        return path


class Tasks(MethodView):
    def get(self, task_id):
        task = AsyncResult(task_id, app=celery)
        return jsonify({'status': task.status,
                        'result': task.result})


class Processed(MethodView):
    def get(self, filename):
        try:
            return send_file(filename, as_attachment=True)
        except FileNotFoundError:
            abort(404)


upscale_view = Upscale.as_view('upscale')
task= Tasks.as_view('task')
processed= Processed.as_view('processed')
app.add_url_rule('/upscale/', view_func=upscale_view, methods=['POST'])
app.add_url_rule('/tasks/<string:task_id>', view_func=task, methods=['GET'])
app.add_url_rule('/processed/<path:filename>', view_func=processed, methods=['GET'])


if __name__ == '__main__':
    app.run(port=5000)
