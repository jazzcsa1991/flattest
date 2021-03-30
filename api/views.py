from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView,DetailView,CreateView,TemplateView
from django.shortcuts import redirect
from api.models import PullRequest
from git import Repo
from git import Git
from github import Github
from django.http import HttpResponse
from datetime import datetime
import os
import sys
import json


try:
    TOKEN = os.environ['TOKEN']
    REPO = os.environ['REPO']
    URL_GIT = os.environ['URL_GIT']
    g = Github(TOKEN)
    repo = g.get_repo(REPO)
except:
    print("falta configurar las variables de entorno")

try:
    import httplib
except:
    import http.client as httplib

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

#funcion para ver si hay internet 
def checkInternetHttplib(url="www.google.com", timeout=3):
    conn = httplib.HTTPConnection(url, timeout=timeout)
    try:
        conn.request("HEAD", "/")
        conn.close()
        return True
    except Exception as e:
        return False
#clase de home que muesra el navbar
class HomeMainView(TemplateView):
    internet_conection = checkInternetHttplib()
    template_name = 'home/home.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['internet'] = self.internet_conection
        return context

#clase que muestra las ra,sde un pullruquest
class BranchesListView(TemplateView):
    template_name = 'branches/branches.html'
    def get_context_data(self,**kwargs):
        context = super().get_context_data(**kwargs)
        repo = setupGit()
        context['branches'] = [str(item).replace('/','_') for item in repo.remote().refs]
        return context

#clase para ver los detalles de una rama
class BranchDetail(TemplateView):
    template_name = 'branches/detailbranch.html'
    def get_context_data(self,**kwargs):
        context = super().get_context_data(**kwargs)
        branch = kwargs['branch']
        commits = branchCommits(branch)
        context['commits'] = commits
        context['branchref'] = branch
        return context

#clase que muestra los detalles de un commit
class CommitDetail(TemplateView):
    template_name = 'branches/commitdetail.html'
    def get_context_data(self,**kwargs):
        context = super().get_context_data(**kwargs)
        branch = kwargs['branch']
        commit = kwargs['commit']
        detail = detailCommits(branch,commit)
        context['detail'] = detail
        context['commit'] = commit
        context['branch'] = branch.replace('_','/')
        return context

#cclase que muestra la lista de tosos los pullrequest creados
class PullRequestCreated(ListView):
    model = PullRequest
    template_name = 'pr/pr_created.html'

#clase de la lista de los PR en un repocitorio
class PRView(TemplateView):
    template_name = 'pr/pr.html'
    def get_context_data(self,**kwargs):
        context = super().get_context_data(**kwargs)
        repo = setupGit()
        context['branches'] = [str(item).replace('/','_') for item in repo.remote().refs]
        return context

#clas eque miestra la lista de los pullreques 
class PRViewList(TemplateView):
    template_name = 'pr/prlist.html'
    def get_context_data(self,**kwargs):
        context = super().get_context_data(**kwargs)
        prs = getPRs()
        context['pulls'] = prs
        return context

#clase que cierra un pullrequest
def closePR(request):
    number = request.POST['number']
    message = closePRgit(int(number))
    return HttpResponse(json.dumps({'message':message}),content_type="application/json")

#view que hace un merge de un pullreuqest
def mergePR(request):
    number = request.POST['number']
    commit = request.POST['commit']
    message = mergePRgit(int(number),commit)
    return HttpResponse(json.dumps({'message':message}),content_type="application/json")

#view que crea un pullrequest
def createPR(request):
    base = request.POST['base'].split('_')[1]
    title = request.POST['title']
    body = request.POST['body']
    commit = request.POST['commit']
    compare = request.POST['compare'].split('_')[1]
    merge = request.POST['merge']
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
