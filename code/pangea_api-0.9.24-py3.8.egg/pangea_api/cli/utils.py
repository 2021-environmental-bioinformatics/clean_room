import click
from .. import Knex, User

class State(object):

    def __init__(self):
        self.email = None
        self.password = None
        self.endpoint = 'https://pangeabio.io'
        self.outfile = None

    def get_knex(self):
        knex = Knex(self.endpoint)
        if self.email and self.password:
            User(knex, self.email, self.password).login()
        return knex

pass_state = click.make_pass_decorator(State, ensure=True)


def email_option(f):
    def callback(ctx, param, value):
        state = ctx.ensure_object(State)
        state.email = str(value)
        return value
    return click.option('-e', '--email',
                        envvar='PANGEA_USER',
                        expose_value=False,
                        help='Your Pangea login email.',
                        callback=callback)(f)


def password_option(f):
    def callback(ctx, param, value):
        state = ctx.ensure_object(State)
        state.password = str(value)
        return value
    return click.option('-p', '--password',
                        envvar='PANGEA_USER',
                        expose_value=False,
                        help='Your Pangea password.',
                        callback=callback)(f)


def endpoint_option(f):
    def callback(ctx, param, value):
        state = ctx.ensure_object(State)
        state.endpoint = str(value)
        return value
    return click.option('--endpoint',
                        default='https://pangeabio.io',
                        expose_value=False,
                        help='The URL to use for Pangea.',
                        callback=callback)(f)


def outfile_option(f):
    def callback(ctx, param, value):
        state = ctx.ensure_object(State)
        state.outfile = value
        return value
    return click.option('-o', '--outfile',
                        default='-', type=click.File('w'),
                        expose_value=False,
                        help='The URL to use for Pangea.',
                        callback=callback)(f)


def common_options(f):
    f = outfile_option(f)
    f = password_option(f)
    f = email_option(f)
    f = endpoint_option(f)
    return f


def use_common_state(f):
    f = common_options(f)
    f = pass_state(f)
    return f


def is_uuid(name):
    chunks = name.split('-')
    return len(chunks) == 5


