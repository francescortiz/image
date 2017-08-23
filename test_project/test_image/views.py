from django.shortcuts import render


def root(request):
    return render(request, 'test_project/root.html')
