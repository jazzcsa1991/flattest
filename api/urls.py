from django.urls import path
from api import views


urlpatterns = [
	path(route='',view =views.HomeMainView.as_view(),name='home'),
    path(route='/branches',view =views.BranchesListView.as_view(),name='branches'),
    path(route='/branches/detail/<str:branch>/',view =views.BranchDetail.as_view(),name='branch-detail'),
    path(route='/branches/detail/<str:commit>/<str:branch>/',view =views.CommitDetail.as_view(),name='commit-detail'),
    path(route='/pr/',view =views.PRView.as_view(),name='pr'),
    path(route='/pr_list/',view =views.PRViewList.as_view(),name='pr_list'),
    path(route='/pr_created/',view =views.PullRequestCreated.as_view(),name='pr_created'),
    path(route='/create',view =views.createPR,name="create"),
    path(route='/close',view =views.closePR,name="close"),
    path(route='/merge',view =views.mergePR,name="merge"),
    ]
