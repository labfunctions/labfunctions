from typing import Any, Dict, List, NewType, Optional, Set, Tuple, Union

from pydantic import BaseModel, BaseSettings

ExtraField = NewType("ExtraField", Dict[str, Any])
AGENT_HOMEDIR = "/home/op"
USER = "op"
DOCKER_UID = "1000"
DOCKER_GID = "997"
AGENT_DOCKER_IMG = "nuxion/labfunctions"


class DestroyRequest(BaseModel):
    cluster_name: str
    machine_name: str


class DeployAgentRequest(BaseModel):
    qnames: List[str] = ["cpu"]
    use_public: bool = True
    docker_image: str = AGENT_DOCKER_IMG
    docker_version: str = "latest"
    worker_procs: int = 2
    user_agent: Optional[str] = None


class RequestAgentToken(BaseModel):
    user_agent: str
    exp: int = 60 * 24


class DeployAgentTask(BaseModel):
    machine_name: str
    cluster_name: str = "default"
    qnames: List[str] = ["cpu"]
    use_public: bool = True
    docker_version: str = "latest"
    docker_image: str = AGENT_DOCKER_IMG
    worker_procs: int = 2


class CreateRequest(BaseModel):
    """
    Main entity for instances creation in a defined cluster

    :param cluster_name: related to cluster spec file
    :param alias: change the default name of a machine
    :param agent: agent deploy options, if none any change will be deployed
    :param timeout: timeot for the task to complete as 5h, 5m, 5s ...
    :param max_retry: take care of this, because actions are not transactionals
    if some step fails, it could result in multiple instances created.
    """

    cluster_name: str
    alias: Optional[str] = None
    agent: Optional[DeployAgentRequest] = None
    timeout: str = "10m"
    max_retry: int = 1


class ClusterSpec(BaseModel):
    """Cluster Specification
    used to group similar machines

    :param name: name of the cluster
    :param machine: name of a machine defined as MachineOrm
    :param provider: which provider should be used: gce, aws, local...
    :param location: location where the machine should be created
    :param network: network to be used
    """

    name: str
    machine: str
    provider: str = "local"
    location: Optional[str] = None
    network: Optional[str] = None


class SSHKey(BaseModel):
    """
    It represents a SSHKey configuration,
    it will have the paths to public and private key
    and user associated to that key
    """

    public_path: str
    private_path: Optional[str] = None
    user: str = "op"


class MachineType(BaseModel):
    """A generic Machine type to be used in MachineModel"""

    size: str
    image: str
    vcpus: int = 1
    network: str = "default"
    extra: Optional[ExtraField] = None


class MachineGPU(BaseModel):
    """A generic representation of GPU resource"""

    name: str
    gpu_type: str
    count: int = 1
    extra: ExtraField = None


class BlockStorage(BaseModel):
    """
    A generic representation of a disk, potentially the mount_point could
    be used to identify if this will be a boot disk (needed in GCE)
    """

    name: str
    size: Union[int, str]
    location: str
    mount: str = "/mnt/disk0"
    create_if_not_exist: bool = False
    snapshot: Optional[str] = None
    image: Optional[str] = None
    permissions: Optional[List[str]] = None
    description: Optional[str] = None
    kind: Optional[str] = None
    extra: Optional[ExtraField] = None


class MachineOrm(BaseModel):
    """Entity representing the MachineModel"""

    name: str
    provider: str
    location: str  # zone
    machine_type: MachineType
    gpu: Optional[MachineGPU] = None
    volumes: List[str] = []
    desc: Optional[str] = None

    class Config:
        orm_mode = True


class MachineRequest(BaseModel):
    """
    Machine Request definition, this will be used as a request to
    create a machine

    A note about tags and labels:
    The main idea behind tags or labels in the context of NBWorkflows,
    is to differentiate machines between clusters. Maybe in the future
    another uses case could emerge.

    Some providers, like GoogleCloud, has the two options
    where the "tags" param is a list used more likely for networking/firewall rules,
    and labels is a dict that could be used for filtering or billing purposes.

    So, in the context of NBWorkflows, only should exist the concept of labels as dict.
    A workaround to address different kind of tags/labels from providers is adopting
    some conventions. For instance if the provider only allows a list of tags,
    it could be serialized in this way:

    .. code-block:
    original_labels = {"cluster": "medium-gpu", "tags": ["nbworkflows", "control_plane"] }
    provider_that_only_accepts_list =
              ["cluster:medium-gpu", "tags:nbworkflows", "tags:control_plane"]


    :param name: the machine will be created with this name, usually
    is build as `machine-type`-`random_id`
    :param size: node type in the vendor cloud parlance
    :param image: image to be used like debian or custom
    :param location: a general term, cloud providers could use zone, region or both
    :param provider: provider name to be used
    :param disks: Disks to be attached to the machine creation
    :param gpu: Optional GPU resource
    :param ssh_public_cert: certificate to be added to authorized_keys
    in the remote host, this should be the string version of the certificate.
    :param ssh_user: to which user allow access.
    :param network: virtual network to configurate
    :param labels:  cluster and other properties to be used
    :param external_ip: the external IP address to use. If ‘dynamic’ (default)
    is up to the provider to asign an ip address. If ‘None’,
    then no external address will be used.
    :param internal_ip: the external IP address to use. If ‘dynamic’ (default)
    is up to the provider to asign an ip address. If ‘None’,
    then no external address will be used.
    :param extra: you should try not to use it, but is here as backup for any edge case.

    """

    name: str
    size: str
    image: str
    location: str  # zone
    provider: str
    internal_ip: Union[str, None] = "dynamic"
    external_ip: Union[str, None] = "dynamic"
    volumes: List[BlockStorage] = []
    gpu: Optional[MachineGPU] = None
    ssh_public_cert: Optional[str] = None
    ssh_user: Optional[str] = "op"
    network: str = "default"
    labels: Optional[Dict[str, Any]] = None
    extra: Optional[ExtraField] = None


class MachineInstance(BaseModel):
    machine_id: str
    machine_name: str
    location: str
    private_ips: List[str]
    public_ips: List[str] = []
    volumes: List[str] = []
    labels: Optional[Dict[str, Any]] = None
    cluster: str = "default"
    extra: Optional[ExtraField] = None


class BlockInstance(BaseModel):
    id: str
    name: str
    size: Union[int, str]
    location: str
    mount: Optional[str] = None
    snapshot: Optional[str] = None
    image: Optional[str] = None
    permissions: Optional[List[str]] = None
    description: Optional[str] = None
    kind: Optional[str] = None
    extra: Optional[ExtraField] = None


class ExecutionMachine(BaseModel):
    execid: str
    machine_name: str
    machine: MachineRequest
    provider: str
    cluster: str = "default"
    qnames: List[str] = []
    agent_homedir: str = AGENT_HOMEDIR
    worker_procs: int = 1
    ssh_key: Optional[SSHKey] = None
    docker_uid: str = DOCKER_UID
    docker_gid: str = DOCKER_GID
    docker_image: str = AGENT_DOCKER_IMG
    docker_version: str = "latest"


class ExecMachineResult(BaseModel):
    execid: str
    private_ips: List[str]
    public_ips: Optional[List[str]] = None
    node: MachineInstance


class ClusterFileType(BaseModel):
    providers: Dict[str, str]
    clusters: Dict[str, ClusterSpec]
    volumes: Dict[str, BlockStorage]
    machines: Dict[str, MachineOrm]


class AgentRequest(BaseModel):
    machine_ip: str
    machine_id: str
    private_key_path: str
    cluster: str
    access_token: str
    refresh_token: str
    web_redis: str
    queue_redis: str
    control_queue: str
    workflow_service: str
    qnames: List[str] = ["cpu"]
    agent_homedir: str = AGENT_HOMEDIR
    agent_name: Optional[str] = None
    advertise_addr: Optional[str] = None
    docker_image: str = AGENT_DOCKER_IMG
    docker_version: str = "latest"
    docker_uid: int = 1089
    docker_gid: int = 997
    docker_registry: Optional[str] = None
    worker_procs: int = 2


class SSHResult(BaseModel):
    command: str
    return_code: int
    stderror: str = ""
    stdout: str = ""
