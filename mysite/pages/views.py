from django.http import HttpResponse
from .models import ToDoList
from .forms import CreateNewList, CourseForm, TaskForm
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.utils import timezone
from .models import Task, WebsiteMeta, Course

import random, math

def index(request):
	template_name = 'pages/base.html'
	return render(request, template_name)
def about(request):
	template_name = 'pages/about.html'
	return render(request, template_name)
def faq(request):
	return HttpResponse("FAQ")

def howto(request):
	return HttpResponse("How To")

def account(request):
	return HttpResponse("Account Page")

def register(response):
	if response.method == "POST":
		form = UserCreationForm(response.POST)
		if form.is_valid():
			form.save()

		return redirect("/")
	else:
		form = UserCreationForm()
	return render(response, "register/register.html", {"form": form})

#See tasks.html for related HTML code
def calendar(request):
	if (request.method == "POST"):
		if ('new_task' in request.POST): #If the form that we submitted has the name 'new_task'
			check_websitemeta()
			t = Task()
			t.description_text = f'Untitled Task {total_tasks_ever_made()}'
			t.time_estimate = 165 #Almost three hours
			t.due_date = timezone.now() + timezone.timedelta(days = 10) #Due ten days from now by default
			t.save()
			update_subtasks(t)
			total_tasks_ever_made(increment=1)
			return HttpResponseRedirect("/calendar") #Need this return to avoid 'confirm form resubmission' thing

		if ('delete_task' in request.POST): #If the form that we submitted has the name 'delete_task'
			id_to_delete = request.POST['task_id'] #Get the ID of the task. This is stored in a input tag of type='hidden'
			Task.objects.filter(id=id_to_delete).delete()
			return HttpResponseRedirect("/calendar")

		if ('edit_task' in request.POST): #If the form that we submitted has the name 'edit_task'
			task_id = request.POST['task_id'] #Get the ID of the task. This is stored in a input tag of type='hidden'
			return HttpResponseRedirect("task_"+task_id + "/edit_task")

	course_list = Course.objects.all()
	tsk_list = Task.objects.all().order_by('-due_date')
	return render(request, 'pages/tasks.html', {'tsk_list': tsk_list, 'course_list': course_list})

#Add subtasks to an existing task
#Subtasks are blocks of automatically scheduled time for someone to work on a larger task 
#Amount of subtasks changes depending on the time estimate of the task,
#and how long each subtask is (defined by the block_time variable)
def update_subtasks(task: Task):
	#Clear any currently existing subtasks, if they exist
	for subtask in task.subtasks.all():
		subtask.delete()
	block_time = 60 #Time in minutes. This means Subtasks are 1 hour blocks of time
	time_remaining = task.time_estimate
	if (time_remaining > block_time):
		num_subtasks = int(math.ceil(time_remaining / block_time))
		days_to_doit = task.due_date - timezone.now()
		days_between_subtasks = days_to_doit / num_subtasks
		#Keep track of initial number of subtasks. 
		#We do this cus the actual number can change as subtasks are completed (deleted)
		#This should probably be removed if the method of completing subtasks ever changes
		task.initial_subtask_count = num_subtasks
		task.save()
		#Actually create and 'attach' our subtasks to the parent task
		for i in range(num_subtasks):
			subtask = Task()
			subtask.description_text = f"Work on {task}"
			subtask.is_subtask = True
			subtask.parent_task = task
			if (time_remaining >= block_time):
				subtask.time_estimate = block_time
			else:
				subtask.time_estimate = time_remaining
			subtask.due_date = timezone.now() + (days_between_subtasks * i) #TODO: Smarter timedelta based on schedule, etc
			subtask.save()
			time_remaining -= block_time

#Currently a placeholder function for handling task editing
def edit_task(request, task_id):
	task = get_object_or_404(Task, pk=task_id)
	form = TaskForm(request.POST, instance = task)
	if request.method == "POST":
		if form.is_valid():
			task = form.save(commit = False)
			task.task = task
			task.save()
			return redirect('/calendar/')
		else:
			form = TaskForm(instance = task)
	return render(request, 'pages/edit_task.html', {"form": form})

#Very similar to the calendar view function above
def courses(request):
	if (request.method == "POST"):
		if ('new_course' in request.POST): #If the form that we submitted has the name 'new_course'
			check_websitemeta()
			c = Course()
			c.name = f'Untitled Course {total_courses_ever_made()}'
			c.color = f"hsl({random.randint(0, 360)}, {random.randint(25, 95)}%, {random.randint(85, 95)}%"
			c.save()
			request.user.course.add(c)
			total_courses_ever_made(increment=1)

		if ('delete_course' in request.POST): #If the form that we submitted has the name 'delete_course'
			id_to_delete = request.POST['course_id'] #Get the ID of the course. This is stored in a input tag of type='hidden'
			Course.objects.filter(id=id_to_delete).delete()

		if ('edit_course' in request.POST): #If the form that we submitted has the name 'edit_course'
			course_id = request.POST['course_id'] #Get the ID of the course. This is stored in a input tag of type='hidden'
			return HttpResponseRedirect("course_"+course_id + "/edit_course")

	course_list = request.user.course.all()
	return render(request, 'pages/courses.html', {'course_list': course_list})


#Currently a placeholder function for handling course editing
def edit_course(request, course_id):
	course = get_object_or_404(Course, pk=course_id)
	form = CourseForm(request.POST, instance = course)
	if request.method == "POST":
		if form.is_valid():
			course = form.save(commit = False)
			course.course = course
			course.save()

			return redirect("/courses/")
		else:
			form = CourseForm(instance =course)
	return render(request, 'pages/edit_course.html',{"form": form} )

def tos(request):
	return HttpResponse("Terms of Service")

#Function for handling view for creating todo lists
def create(response):
	if response.method == "POST":
		form = CreateNewList(response.POST)
		if form.is_valid():
			n = form.cleaned_data["name"]
			t = ToDoList(name=n)
			t.save()

		return HttpResponseRedirect("/%i" %t.id)
	else:
		form = CreateNewList()
	return render(response, "pages/create.html", {"form": form})

#Check to see if we have a 'WebsiteMeta' object in the database. If not, add one
def check_websitemeta():
	#Use objects.all() to get a list of all 'WebsiteMeta' objects (there should only really be one)
	num_website_metas = len(WebsiteMeta.objects.all())
	if (num_website_metas == 0):
		print("No WebsiteMeta object found, creating a new one.")
		wm = WebsiteMeta()
		wm.save()
	elif(num_website_metas != 1):
		#We should only ever have one max, so if there's more than 1 raise an error
		raise Exception("More than one WebsiteMeta object found, only 1 should exist at a time. Please let Emmanuel know about this!")

#Function to get or set the total tasks ever made by the website. Uses the 'WebsiteMeta' database entry to keep track of this
def total_tasks_ever_made(increment = 0):
	check_websitemeta() #Make sure we have a websitemeta object to work with
	wm = WebsiteMeta.objects.all()[0] #Get the first (and only) WebsiteMeta object from our database
	wm.total_tasks_created += increment
	wm.save()
	return wm.total_tasks_created

def total_courses_ever_made(increment = 0):
	check_websitemeta() #Make sure we have a websitemeta object to work with
	wm = WebsiteMeta.objects.all()[0] #Get the first (and only) WebsiteMeta object from our database
	wm.total_courses_created += increment
	wm.save()
	return wm.total_courses_created
