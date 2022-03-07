# pylint: disable=too-few-public-methods
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import BYTEA, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy_serializer import SerializerMixin

from nb_workflows.db.common import Base


class HistoryModel(Base, SerializerMixin):
    """
    Register each execution of a workflow.

    :param jobid: Is the workflow jobid
    :param taskid: is random id generated for each execution of the workflow
    :param name: the filename of the notebook executed
    :param result: is the result of the task. TaskResult
    :param elapsed_secs: Time in seconds from the start of the task to the end.
    :param status: -1 fail, 0 ok.
    """

    __tablename__ = "nb_workflows_history"
    __mapper_args__ = {"eager_defaults": True}

    id = Column(BigInteger, primary_key=True)
    jobid = Column(String(24))
    executionid = Column(String(24))  # should be execution id
    nb_name = Column(String(), nullable=False)
    result = Column(JSONB(), nullable=False)
    elapsed_secs = Column(Float(), nullable=False)
    status = Column(Integer, index=True)
    # code = Column(BigInteger, index=True, unique=True, nullable=False)
    created_at = Column(DateTime(), default=datetime.utcnow(), nullable=False)


class ProjectModel(Base, SerializerMixin):
    """
    Register each execution of a workflow.

    :param jobid: Is the workflow jobid
    :param taskid: is random id generated for each execution of the workflow
    :param name: the filename of the notebook executed
    :param result: is the result of the task. TaskResult
    :param elapsed_secs: Time in seconds from the start of the task to the end.
    :param status: -1 fail, 0 ok.
    """

    __tablename__ = "nb_core_project"
    __mapper_args__ = {"eager_defaults": True}

    id = Column(BigInteger, primary_key=True)
    projectid = Column(String(16), index=True, unique=True, nullable=False)
    name = Column(String(128), nullable=False)
    private_key = Column(BYTEA(), nullable=False)
    description = Column(String())
    repository = Column(String(2048), nullable=True)
    user_id = Column(
        BigInteger,
        ForeignKey("nb_auth_user.id", ondelete="SET NULL"),
        nullable=False,
    )

    user = relationship("UserModel")
    # folder = Column(String(24))  # should be execution id
    created_at = Column(DateTime(), default=datetime.utcnow(), nullable=False)
    updated_at = Column(DateTime(), default=datetime.utcnow())


class WorkflowModel(Base, SerializerMixin):
    """
    Configuration for each workflow.

    :param jobid: an unique identifier for this workflow
    :param alias: because the filename could be shared between different
    workflows, an alias was added to identify each instance, and is more
    friendly than jobid.
    :param name: name of the notebook file.
    :param description: A friendly description of the purpose of this workflow
    :param job_detail: details of the execution. It is composed by two nested
    entities: ScheduleData and NBTask.
    :param enabled: if the task should run or not.
    """

    # pylint: disable=too-few-public-methods
    __tablename__ = "nb_core_workflow"
    __table_args__ = (
        UniqueConstraint("alias", "project_id", name="_nb_workflow__project_alias"),
    )
    # needed for async support
    __mapper_args__ = {"eager_defaults": True}

    id = Column(Integer, primary_key=True)
    jobid = Column(String(24), index=True, unique=True)
    alias = Column(String(33), index=True, nullable=False)
    nb_name = Column(String(), nullable=False)
    job_detail = Column(JSONB(), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    # project_id = Column(BigInteger, ForeignKey(
    #    'nb_workflows_project.id', ondelete='SET NULL'), nullable=True)
    # project = relationship("ProjectModel")
    project_id = Column(
        String(16),
        ForeignKey("nb_core_project.projectid", ondelete="SET NULL"),
        nullable=True,
    )
    project = relationship("ProjectModel")

    created_at = Column(DateTime(), default=datetime.utcnow(), nullable=False)
    updated_at = Column(DateTime(), default=datetime.utcnow())