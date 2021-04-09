import os
import json
from git import Repo,Git
from github import Github
from datetime import datetime
from api.models import PullRequest
from django.shortcuts import render
from rest_framework import viewsets
from django.http import HttpResponse
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from api.serializer import BranchSerializer,CommitSerializer,CommitDetailSerializer,PRListSerializer,PullRequestSerializer

try:
    TOKEN = os.environ['TOKEN']
    REPO = os.environ['REPO']
    URL_GIT = os.environ['URL_GIT']
    g = Github(TOKEN)
    repo = g.get_repo(REPO)
except:
    print("falta configurar las variables de entorno")

#funcion para tarer una lista de los pull request
def getPRs():
    pulls = repo.get_pulls(state='all', sort='created')
    return pulls

#funcion para cerrar un pullrequest
def closePRgit(number):
    pr = repo.get_pull(number)
    try :
        pr.edit(state="closed")
        return "cerrado correctamente"
    except:
        return "ocurrio un error"

#funcion para hacer un merge 
def mergePRgit(number,commit):
    pr = repo.get_pull(number)
    try :
        pr = pr.merge(commit_message=commit)
        return"commit:"+pr.sha + " "+ pr.message
    except Exception as e:
        return e.data['message']

#funcion para clonar un directotio o hacer pull
def setupGit():
    local_repo_directory = os.path.join(os.getcwd(), 'repogit')
    destination = 'master'
    if os.path.exists(local_repo_directory):
        repo = Repo(local_repo_directory)
        origin = repo.remotes.origin
        origin.pull()
    else:
        Repo.clone_from(URL_GIT,local_repo_directory)
        repo = Repo(local_repo_directory)
    return repo

#ufuncion para ver todas las rams de un directorio
def branchCommits(branch):
    branch = branch.replace('_','/')
    repo = setupGit()
    commits = list(repo.iter_commits(branch))
    commit_list = []
    for commit in commits:
        temp = dict()
        temp['commit'] = commit
        temp['message'] = commit.message
        temp['author'] = commit.author.name
        temp['date'] = datetime.utcfromtimestamp(commit.committed_date)
        commit_list.append(temp)
    return commit_list

#funcion para ver los detalles de un comit
def detailCommits(branch,commitid):
    branch = branch.replace('_','/')
    repo = setupGit()
    commits = list(repo.iter_commits(branch))
    commit_list = []
    for commit in commits:
        if str(commit) == commitid:
            temp = dict()
            temp['message'] = commit.message
            temp['date'] = datetime.utcfromtimestamp(commit.committed_date)
            temp['files'] = commit.stats.total['files']
            temp['author'] = commit.author.name
            temp['mail'] = commit.author.email
            commit_list.append(temp)
    return commit_list[0]

class PRListBackup(viewsets.ModelViewSet):
    """
    una simple VIew set para listar todos los pull
    request creados y ver como fueron creados
    """
    queryset = PullRequest.objects.all()
    serializer_class = PullRequestSerializer
    
class PRListViewSet(viewsets.ViewSet):
    """
    una simple VIew set para listar todos los pull
    request que se tienen en un repo y cerrarlos o modificarlos si fuera necesario 
    """
    def list(self,request):
        prs = getPRs()
        serializer = PRListSerializer(prs,many=True)
        return Response(serializer.data)

    def create(self,request):
        base = request.data['base'].split('_')[1]
        title = request.data['title']
        body = request.data['body']
        commit = request.data['commit']
        compare = request.data['compare'].split('_')[1]
        merge = request.data['merge']
        if merge == 'true':
            try:
                pr = repo.create_pull(title=title, body=body, head=compare, base=base)
                pr = pr.merge(commit_message=commit)
                pr_create = PullRequest.objects.create(
                    author =  pr.user,
                    title = pr.title,
                    description = pr.body,
                    status = pr.state
                )
                message = "commit:"+pr.sha + " "+ pr.message
            except Exception as e:
                message = e.data['message']+": " + e.data['errors'][0]['message']
        else:
            try:
                pr = repo.create_pull(title=title, body=body, head=compare, base=base)
                pr_create = PullRequest.objects.create(
                    author =  pr.user,
                    title = pr.title,
                    description = pr.body,
                    status = pr.state
                )
                message = "Title:"+pr.title + " "+ "number:"+ str(pr.number)
            except Exception as e:
                message = e.data['message']+": " + e.data['errors'][0]['message']
        return HttpResponse(json.dumps({'message':message}),content_type="application/json")

    @action(methods=['post'],detail=True)
    def mergePR(self,request,pk=None):
        number = request.data['number']
        commit = request.data['commit']
        message = mergePRgit(int(number),commit)
        return HttpResponse(json.dumps({'message':message}),content_type="application/json")

    @action(methods=['post'],detail=True)
    def closePR(self,request,pk=None):
        number = request.data['number']
        message = closePRgit(int(number))
        return HttpResponse(json.dumps({'message':message}),content_type="application/json")

class BranchViewSet(viewsets.ViewSet):
    """
    una simple viewset para listar todas las ramas de un repo, 
    ver los commits de cada repo y el detalle de los commits
    """
    def list(self, request):
        repo = setupGit()
        branches= [str(item).replace('/','_') for item in repo.remote().refs]
        branches2= [{"branch":str(item).replace('/','_')} for item in repo.remote().refs]
        serializer = BranchSerializer(branches2, many=True)
        return Response(serializer.data)

    @action(methods=['get'],detail=True)
    def commit(self,request,pk=None, *args, **kwargs):
        commit = request.GET.get('commit', None)
        branch = pk.replace('_','/')
        branch = branch.replace('"','')
        repo = setupGit()
        commits = list(repo.iter_commits(branch))
        commit_list = []
        commitf = commit.replace('"',"")
        for commit in commits:
            if str(commit) == commitf:
                temp = dict()
                temp['message'] = commit.message
                temp['date'] = datetime.utcfromtimestamp(commit.committed_date)
                temp['files'] = commit.stats.total['files']
                temp['author'] = commit.author.name
                temp['mail'] = commit.author.email
                commit_list.append(temp)
        serializer = CommitDetailSerializer(commit_list, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        branch = pk.replace('_','/')
        branch = branch.replace('"','')
        repo = setupGit()
        commits = list(repo.iter_commits(branch))
        commit_list = []
        for commit in commits:
            temp = dict()
            temp['commit'] = commit
            temp['message'] = commit.message
            temp['author'] = commit.author.name
            temp['date'] = datetime.utcfromtimestamp(commit.committed_date)
            commit_list.append(temp)
        serializer = CommitSerializer(commit_list, many=True)
        return Response(serializer.data)




