from datetime import datetime

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponseRedirect, Http404

import jingo

from sumo.urlresolvers import reverse
from .models import Document, Revision, CATEGORIES
from .forms import DocumentForm, RevisionForm, ReviewForm


def document(request, document_slug):
    """View a wiki document."""
    # This may change depending on how we decide to structure
    # the url and handle locales.
    doc = get_object_or_404(
        Document, locale=request.locale, slug=document_slug)
    return jingo.render(request, 'wiki/document.html',
                        {'document': doc})


def list_documents(request, category=None):
    """List wiki documents."""
    docs = Document.objects.all()
    if category:
        docs = docs.filter(category=category)
        try:
            category_id = int(category)
        except ValueError:
            raise Http404
        try:
            category = unicode(dict(CATEGORIES)[category_id])
        except KeyError:
            raise Http404
    return jingo.render(request, 'wiki/list_documents.html',
                        {'documents': docs,
                         'category': category})


@login_required
@permission_required('wiki.add_document')
def new_document(request):
    """Create a new wiki document."""
    if request.method == 'GET':
        doc_form = DocumentForm()
        rev_form = RevisionForm()
        return jingo.render(request, 'wiki/new_document.html',
                            {'document_form': doc_form,
                             'revision_form': rev_form})

    doc_form = DocumentForm(request.POST)
    rev_form = RevisionForm(request.POST)

    if doc_form.is_valid() and rev_form.is_valid():
        doc = doc_form.save()

        doc.firefox_versions = doc_form.cleaned_data['firefox_versions']
        doc.operating_systems = doc_form.cleaned_data['operating_systems']

        rev = rev_form.save(commit=False)
        rev.document = doc
        rev.creator = request.user
        rev.save()

        return HttpResponseRedirect(reverse('wiki.document_revisions',
                                    args=[doc.slug]))

    return jingo.render(request, 'wiki/new_document.html',
                        {'document_form': doc_form,
                         'revision_form': rev_form})


@login_required
@permission_required('wiki.add_revision')
def new_revision(request, document_slug, revision_id=None):
    """Create a new revision of a wiki document."""
    doc = get_object_or_404(
        Document, locale=request.locale, slug=document_slug)
    if revision_id:
        rev = get_object_or_404(Revision, pk=revision_id, document=doc)
    elif doc.current_revision:
        rev = doc.current_revision
    else:
        rev = doc.revisions.order_by('-created')[0]

    if request.method == 'GET':
        initial = {
            'keywords': rev.keywords,
            'content': rev.content,
            'summary': rev.summary,
        }
        rev_form = RevisionForm(initial=initial)

        # If the Document doesn't have a current_revision (nothing approved)
        # then all the Document fields are still editable. Once there is an
        # approved Revision, the Document fields are locked.
        if not doc.current_revision:
            initial = {
                'title': doc.title,
                'category': doc.category,
                'tags': ','.join([t.name for t in doc.tags.all()]),
                'firefox_versions': [x.item_id for x in
                                     doc.firefox_versions.all()],
                'operating_systems': [x.item_id for x in
                                      doc.operating_systems.all()],
            }
            doc_form = DocumentForm(initial=initial)
        else:
            doc_form = None

        return jingo.render(request, 'wiki/new_revision.html',
                            {'revision_form': rev_form,
                             'document_form': doc_form,
                             'document': doc})

    rev_form = RevisionForm(request.POST)
    if not doc.current_revision:
        doc_form = DocumentForm(request.POST)
    else:
        doc_form = None

    if rev_form.is_valid() and (not doc_form or doc_form.is_valid()):
        if doc_form:
            document = doc_form.save(commit=False)
            document.id = doc.id
            document.save()

            # TODO: Use the tagging widget instead of this?
            tags = doc_form.cleaned_data['tags']
            doc.tags.exclude(name__in=tags).delete()
            doc.tags.add(*tags)

            ffv = doc_form.cleaned_data['firefox_versions']
            doc.firefox_versions.exclude(
                item_id__in=[x.item_id for x in ffv]).delete()
            doc.firefox_versions = ffv
            os = doc_form.cleaned_data['operating_systems']
            doc.operating_systems.exclude(
                item_id__in=[x.item_id for x in os]).delete()
            doc.operating_systems = os

        new_rev = rev_form.save(commit=False)
        new_rev.document = doc
        new_rev.creator = request.user
        new_rev.based_on = rev
        new_rev.save()

        return HttpResponseRedirect(reverse('wiki.document_revisions',
                                            args=[document_slug]))

    return jingo.render(request, 'wiki/new_revision.html',
                        {'revision_form': rev_form,
                         'document_form': doc_form,
                         'document': doc})


def document_revisions(request, document_slug):
    """List all the revisions of a given document."""
    doc = get_object_or_404(
        Document, locale=request.locale, slug=document_slug)
    revs = Revision.objects.filter(document=doc).order_by('-created')

    return jingo.render(request, 'wiki/document_revisions.html',
                        {'revisions': revs, 'document': doc})


@login_required
@permission_required('wiki.review_revision')
def review_revision(request, document_slug, revision_id):
    """Review a revision of a wiki document."""
    rev = get_object_or_404(Revision, pk=revision_id,
                            document__slug=document_slug)
    doc = rev.document
    form = ReviewForm()

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid() and not rev.reviewed:
            # Don't allow revisions to be reviewed twice
            rev.is_approved = 'approve' in request.POST
            rev.reviewer = request.user
            rev.reviewed = datetime.now()
            rev.comment = form.cleaned_data['comment']
            if rev.is_approved:
                rev.significance = form.cleaned_data['significance']
            rev.save()

            return HttpResponseRedirect(reverse('wiki.document_revisions',
                                                args=[document_slug]))

    return jingo.render(request, 'wiki/review_revision.html',
                        {'revision': rev, 'document': doc, 'form': form})


def compare_revisions(request, document_slug):
    """Compare two wiki document revisions.

    The ids are passed as query string parameters (to and from).

    """
    doc = get_object_or_404(
        Document, locale=request.locale, slug=document_slug)
    if 'from' not in request.GET or 'to' not in request.GET:
        raise Http404

    revision_from = get_object_or_404(Revision, document=doc,
                                      id=request.GET.get('from'))
    revision_to = get_object_or_404(Revision, document=doc,
                                    id=request.GET.get('to'))

    return jingo.render(request, 'wiki/compare_revisions.html',
                        {'document': doc, 'revision_from': revision_from,
                         'revision_to': revision_to})
