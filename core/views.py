import json
import anthropic
import pdfplumber
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import UserProfile, Resume, Conversation, Message
from .forms import UserProfileForm, ResumeUploadForm, RegisterForm


def home(request):
    if request.user.is_authenticated:
        return redirect('chat')
    feature_list = [
        ('fa-solid fa-magnifying-glass-chart', 'Skill Gap Analysis', 'Identify missing skills and get a personalized learning roadmap.'),
        ('fa-solid fa-file-lines', 'Resume Feedback', 'Upload your PDF resume and get detailed AI-powered review.'),
        ('fa-solid fa-comments', 'Interview Prep', 'Practice with realistic interview questions for your target role.'),
        ('fa-solid fa-briefcase', 'Job Search Tips', 'Strategies to land your next developer position faster.'),
    ]
    return render(request, 'core/home.html', {'feature_list': feature_list})


def register(request):
    if request.user.is_authenticated:
        return redirect('chat')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)
            login(request, user)
            messages.success(request, 'Account created! Set up your profile to get started.')
            return redirect('profile_setup')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
def profile_setup(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('chat')
    else:
        form = UserProfileForm(instance=profile)
    active_resume = Resume.objects.filter(user=request.user, is_active=True).first()
    return render(request, 'core/profile_setup.html', {'form': form, 'active_resume': active_resume})


@login_required
def resume_upload(request):
    if request.method == 'POST':
        form = ResumeUploadForm(request.POST, request.FILES)
        if form.is_valid():
            resume = form.save(commit=False)
            resume.user = request.user
            Resume.objects.filter(user=request.user).update(is_active=False)
            try:
                with pdfplumber.open(resume.file) as pdf:
                    text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
                resume.extracted_text = text.strip()
            except Exception:
                resume.extracted_text = ''
            resume.save()
            messages.success(request, 'Resume uploaded and processed successfully!')
            return redirect('profile_setup')
    else:
        form = ResumeUploadForm()
    resumes = Resume.objects.filter(user=request.user)
    return render(request, 'core/resume_upload.html', {'form': form, 'resumes': resumes})


@login_required
def chat(request, conversation_id=None):
    conversations = Conversation.objects.filter(user=request.user)
    current_conversation = None
    chat_messages = []

    if conversation_id:
        current_conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
        chat_messages = current_conversation.messages.all()
    elif conversations.exists():
        current_conversation = conversations.first()
        chat_messages = current_conversation.messages.all()

    profile = getattr(request.user, 'profile', None)
    profile_complete = bool(
        profile and profile.skills and profile.experience_level
    )

    starter_prompts = [
        'Analyze my skill gaps for a senior backend role',
        'Review my resume and suggest improvements',
        'Give me 5 system design interview questions',
        'How do I negotiate a higher salary offer?',
    ]

    return render(request, 'core/chat.html', {
        'conversations': conversations,
        'current_conversation': current_conversation,
        'chat_messages': chat_messages,
        'profile_complete': profile_complete,
        'starter_prompts': starter_prompts,
    })


@login_required
@require_POST
def new_conversation(request):
    conversation = Conversation.objects.create(user=request.user, title='New Conversation')
    return redirect('chat_conversation', conversation_id=conversation.id)


@login_required
@require_POST
def delete_conversation(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
    conversation.delete()
    return redirect('chat')


@login_required
@require_POST
def send_message(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    conversation_id = data.get('conversation_id')
    user_content = data.get('message', '').strip()

    if not user_content:
        return JsonResponse({'error': 'Message cannot be empty'}, status=400)

    if conversation_id:
        conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
    else:
        conversation = Conversation.objects.create(
            user=request.user,
            title=user_content[:60]
        )

    Message.objects.create(conversation=conversation, role='user', content=user_content)

    if conversation.messages.count() == 1:
        conversation.title = user_content[:60]
        conversation.save()

    profile = getattr(request.user, 'profile', None)
    resume = Resume.objects.filter(user=request.user, is_active=True).first()
    system_prompt = _build_system_prompt(request.user, profile, resume)

    history = [
        {'role': msg.role, 'content': msg.content}
        for msg in conversation.messages.all()
    ]

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=2048,
            system=system_prompt,
            messages=history,
        )
        assistant_content = response.content[0].text
    except Exception as e:
        return JsonResponse({'error': f'AI error: {str(e)}'}, status=500)

    Message.objects.create(conversation=conversation, role='assistant', content=assistant_content)
    conversation.save()

    return JsonResponse({
        'response': assistant_content,
        'conversation_id': conversation.id,
        'conversation_title': conversation.title,
    })


def _build_system_prompt(user, profile, resume):
    prompt = (
        f"You are an AI-powered career assistant for software developers. "
        f"You help {user.first_name or user.username} with personalized career guidance.\n\n"
        "You specialize in:\n"
        "- Skill gap analysis and learning roadmaps\n"
        "- Resume review and improvement feedback\n"
        "- Interview preparation and practice questions\n"
        "- Job search strategies and tips\n"
        "- Career path planning and progression\n\n"
        "Be specific, actionable, and encouraging. Use markdown for structured responses."
    )

    if profile:
        if profile.skills:
            prompt += f"\n\nUser's current skills: {profile.skills}"
        if profile.experience_level:
            prompt += f"\nExperience level: {profile.get_experience_level_display()}"
        if profile.job_preferences:
            prompt += f"\nJob preferences: {profile.job_preferences}"
        if profile.bio:
            prompt += f"\nAbout: {profile.bio}"

    if resume and resume.extracted_text:
        prompt += f"\n\nUser's resume content:\n{resume.extracted_text[:4000]}"

    return prompt
