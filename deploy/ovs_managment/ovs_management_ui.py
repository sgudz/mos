import ovs_management
import ConfigParser

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from flask import Flask
from flask import render_template
from flask import request

app = Flask(__name__)
config = ConfigParser.RawConfigParser()
config.read('ovs_management.cfg')

db_url = config.get('db', 'db_url')

Base = declarative_base()
engine = create_engine(db_url, echo=False)
Base.metadata.create_all(engine)
session = sessionmaker(bind=engine)
my_session = session()


@app.route("/", methods=['GET'])
def servers_list():
    lab_db = ovs_management.LabDatabase(my_session)
    show_int = request.args.get('show_int', type=bool)
    env = request.args.get('env')
    env_change = request.args.get('env_change')
    server_ids = request.args.getlist('server_id')
    if len(server_ids) > 0:
        if env_change != "" and env_change != "0":
            for server_id in server_ids:
                lab_db.assign_server_to_env_by_id(server_id, int(env_change))
        elif env_change == "0":
            for server_id in server_ids:
                lab_db.remove_server_from_env_by_id(server_id)
    env_list = lab_db.list_all_env()
    table = lab_db.list_servers_in_env(env)
    return render_template('table.html', table=table, show_int=show_int,
                           envs=env_list, env=env)


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
