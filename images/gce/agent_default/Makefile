.EXPORT_ALL_VARIABLES:
DOCKER_VERSION:=0.9.0
IMG_VERSION:=090

.PHONY: init
init:
	packer init .

.PHONY: validate
validate:
	packer validate -var "docker_lab_version=${DOCKER_VERSION}" -var "img_version=${IMG_VERSION}" .

.PHONY: build
build: validate
	packer build -force -var "docker_lab_version=${DOCKER_VERSION}" -var "img_version=${IMG_VERSION}" .
