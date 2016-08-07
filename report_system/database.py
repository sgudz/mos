#!/usr/bin/python

from sqlalchemy import create_engine
from sqlalchemy.sql import text
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (Column, Integer, String, DateTime,
                        SmallInteger, Sequence, Text)

DB_URL = 'postgresql://rally:Ra11y@172.18.160.54/rally'
Base = declarative_base()

JOB_ID_SEQ = Sequence('job_id_seq')


class JobInfoRecord(Base):
    __tablename__ = 'jobs_info'

    uuid = Column(String(36), primary_key=True)
    id = Column(Integer, JOB_ID_SEQ, primary_key=True,
                server_default=JOB_ID_SEQ.next_value())
    started = Column(DateTime)
    ended = Column(DateTime)
    job_name = Column(String(256))
    bug_id = Column(String(1024))
    parent_job_id = Column(Integer)
    env = Column(SmallInteger)
    contact_person = Column(String(100))
    description = Column(Text)
    job_settings = Column(Text)
    report_dir = Column(String(256))
    log_snapshot = Column(String(1024))
    job_type = Column(String(64))

    def print_out(self):
        return "<JOB(uuid='%s', job_name='%s', id ='%s', env = '%s')>" % (
            self.uuid, self.job_name, self.id, self.env)


class EnvStatus(Base):
    __tablename__ = 'env_status'

    fuel_job_id = Column(Integer)
    cluster_job_id = Column(Integer)
    env = Column(SmallInteger, primary_key=True)


def create_all():
    engine = create_engine(DB_URL, convert_unicode=True, echo=False)
    Base.metadata.create_all(engine)


def add_cluster_record(**kwargs):
    engine = create_engine(DB_URL, convert_unicode=True, echo=False)
    db_session = scoped_session(sessionmaker(bind=engine))
    res = db_session.execute(
        text('INSERT INTO jobs_info (uuid) VALUES (:uuid) RETURNING (id)'),
        {'uuid': kwargs['uuid']}
    )
    db_session.commit()
    db_session.close()
    return res.fetchall()[0][0]


def add_job_record(**kwargs):
    engine = create_engine(DB_URL, convert_unicode=True, echo=False)
    db_session = scoped_session(sessionmaker(bind=engine))
    new_job = JobInfoRecord(uuid=kwargs['uuid']
                            if 'uuid' in kwargs else None,
                            job_name=kwargs['job_name']
                            if 'job_name' in kwargs else None,
                            started=kwargs['started']
                            if 'started' in kwargs else None,
                            ended=kwargs['ended']
                            if 'ended' in kwargs else None,
                            parent_job_id=kwargs['parent_job_id']
                            if 'parent_job_id' in kwargs else None,
                            env=kwargs['env']
                            if 'env' in kwargs else None,
                            bug_id=kwargs['bug_id']
                            if 'bug_id' in kwargs else None,
                            contact_person=kwargs['contact_person']
                            if 'contact_person' in kwargs else None,
                            description=kwargs['description']
                            if 'description' in kwargs else None,
                            job_settings=kwargs['job_settings']
                            if 'job_settings' in kwargs else None,
                            job_type=kwargs['job_type']
                            if 'job_type' in kwargs else None,
                            report_dir=kwargs['report_dir']
                            if 'report_dir' in kwargs else None,
                            log_snapshot=kwargs['log_snapshot']
                            if 'log_snapshot' in kwargs else None)
    db_session.add(new_job)
    db_session.commit()
    rec_id = new_job.id
    db_session.close()
    return rec_id


def get_all_records_from_table(table_class, filter_obj=None, order_exp=None):
    engine = create_engine(DB_URL, convert_unicode=True, echo=False)
    db_session = scoped_session(sessionmaker(bind=engine))
    if filter_obj is not None:
        if order_exp is not None:
            found_jobs = db_session.query(table_class).filter(filter_obj).\
                order_by(order_exp).all()
        else:
            found_jobs = db_session.query(table_class).filter(filter_obj).all()
    else:
        if order_exp is not None:
            found_jobs = db_session.query(table_class).\
                order_by(order_exp).all()
        else:
            found_jobs = db_session.query(table_class).all()

    jobs_list = []
    for job in found_jobs:
        record = job.__dict__
        if record['ended'] is not None and record['started'] is not None:
            record['duration'] = record['ended'] - record['started']
        jobs_list.append(record)

    db_session.close()
    return jobs_list


def update_column_record_in_table(table_class, filter_obj, column_name,
                                  column_value):
    engine = create_engine(DB_URL, convert_unicode=True, echo=False)
    db_session = scoped_session(sessionmaker(bind=engine))
    found_job = db_session.query(table_class).filter(filter_obj).first()
    setattr(found_job, column_name, column_value)
    db_session.commit()
    db_session.close()


def update_env_status(env_num, record_id, fuel=False):
    engine = create_engine(DB_URL, convert_unicode=True, echo=False)
    db_session = scoped_session(sessionmaker(bind=engine))
    found_rec = db_session.query(EnvStatus).filter(
        EnvStatus.env.__eq__(env_num)).first()

    if found_rec is None:
        found_rec = EnvStatus(env=env_num, fuel_job_id=0, cluster_job_id=0)
        db_session.add(found_rec)
        db_session.commit()

    if fuel:
        found_rec.fuel_job_id = record_id
        found_rec.cluster_job_id = 0
    else:
        found_rec.cluster_job_id = record_id

    db_session.commit()
    db_session.close()


def get_job_id_from_env_status(env_num, fuel=False):
    engine = create_engine(DB_URL, convert_unicode=True, echo=False)
    db_session = scoped_session(sessionmaker(bind=engine))
    found_rec = db_session.query(EnvStatus).filter(
        EnvStatus.env.__eq__(env_num)).first()

    if found_rec is None:
        return 0

    if fuel:
        job_id = found_rec.fuel_job_id
    else:
        job_id = found_rec.cluster_job_id

    db_session.close()
    return job_id


def update_job_record(**kwargs):
    engine = create_engine(DB_URL, convert_unicode=True, echo=False)
    db_session = scoped_session(sessionmaker(bind=engine))
    record_id = kwargs['record_id'] if 'record_id' in kwargs else None
    if record_id is None:
        return False

    found_rec = db_session.query(JobInfoRecord).filter(
        JobInfoRecord.id.__eq__(record_id)).first()

    if found_rec is None:
        return False

    found_rec.bug_id = kwargs['bug_id'] if 'bug_id' in kwargs else None
    found_rec.description = kwargs['description']\
        if 'description' in kwargs else None
    found_rec.contact_person = kwargs['contact_person']\
        if 'contact_person' in kwargs else None
    found_rec.job_settings = kwargs['job_settings']\
        if 'job_settings' in kwargs else None
    found_rec.log_snapshot = kwargs['log_snapshot']\
        if 'log_snapshot' in kwargs else None

    db_session.commit()
    db_session.close()
    return True
