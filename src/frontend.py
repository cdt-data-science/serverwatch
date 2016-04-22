from flask import Blueprint, render_template, flash, redirect, url_for
from flask_bootstrap import __version__ as FLASK_BOOTSTRAP_VERSION
from flask_nav.elements import Navbar, View, Subgroup, Link, Text, Separator
from markupsafe import escape

from nav import nav

from remote import RemoteStats, LocalStats

frontend = Blueprint('frontend', __name__)

nav.register_element('frontend_top', Navbar(
    View('Watchatron-2000', '.index'),
    View('Home', '.index'),
    View('Stats', '.statistics')
))

stats = RemoteStats()

@frontend.route('/')
def index():
    names = sorted(stats.get_stats().keys())
    return render_template(
        'index.html',
        servers=stats.get_stats(),
        server_names=names,
        updated=stats.get_time_updated()
    )


@frontend.route('/force_update')
def force_update():
    stats.update_stats()
    return index()


@frontend.route('/stats')
def statistics():
    lstats = LocalStats(stats.get_stats())

    return render_template(
        'stats.html',
        stats=lstats.get_stats()
    )
