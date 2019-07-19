# -*- coding: utf-8 -*-

"""Views for the website."""

from flask import flash, redirect, render_template, url_for

from website import app
from website.forms import ContactForm, NewConnectionForm, RechargeForm
from website.models import JobVacancy


@app.route('/')
def index():
    """Route for homepage."""
    return render_template('index.html')


@app.route('/tariff/<loc>')
def tariff(loc):
    """Route for tariffs."""
    if loc == 'kol':
        plans = []
    elif loc == 'wb':
        plans = []

    return render_template('tariff.html', loc=loc, plans=plans)


@app.route('/downloads')
def downloads():
    """Route for downloads."""
    return render_template('downloads.html')


@app.route('/privacy')
def privacy():
    """Route for privacy."""
    return render_template('privacy.html')


@app.route('/recharge')
def recharge():
    """Route for recharge."""
    form = RechargeForm()

    if form.validate_on_submit():
        flash('Recharge completed!', 'success')
        return redirect(url_for('recharge'))

    return render_template('recharge.html')


@app.route('/new_connection')
def new_conn():
    """Route for new connection."""
    form = NewConnectionForm()

    if form.validate_on_submit():
        flash('Request sent successfully!', 'success')
        return redirect(url_for('new_conn'))

    return render_template('new_connection.html')


@app.route('/careers')
def careers():
    """Route for careers."""
    # items = JobVacancy.query().all()
    return render_template('careers.html', items=items)


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    """Route for contact."""
    form = ContactForm()

    if form.validate_on_submit():
        flash('Message sent successfully!', 'success')
        return redirect(url_for('contact'))

    return render_template('contact.html', form=form)
