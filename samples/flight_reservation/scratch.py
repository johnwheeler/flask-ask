import click
from transitions.extensions import GraphMachine as Machine


class Reservations(object):

    states = ['initial', 'welcome', 'from_city', 'from_date', 'one_way', 'to_date', 'confirm', 'booked']

    def __init__(self):
        self.session = dict()
        self.machine = Machine(self, states=Reservations.states, initial='initial')

        self.machine.add_transition('advance', 'initial', 'welcome')

        self.machine.add_transition('advance', 'welcome', 'from_city')

        self.machine.add_transition('advance', 'from_city', 'from_date', conditions='has_from_city')
        self.machine.add_transition('advance', 'from_city', 'from_city')

        self.machine.add_transition('advance', 'from_date', 'one_way', conditions='has_from_date')
        self.machine.add_transition('advance', 'from_date', 'from_date')

        self.machine.add_transition('advance', 'one_way', 'confirm', conditions='is_trip_one_way')
        self.machine.add_transition('advance', 'one_way', 'to_date', conditions='has_one_way')
        self.machine.add_transition('advance', 'one_way', 'one_way')

        self.machine.add_transition('advance', 'to_date', 'confirm', conditions='has_to_date')
        self.machine.add_transition('advance', 'to_date', 'to_date')

        self.machine.add_transition('advance', 'confirm', 'booked', conditions='is_trip_confirm')
        self.machine.add_transition('advance', 'confirm', 'from_city', unless='is_trip_confirm')
        self.machine.add_transition('advance', 'confirm', 'confirm')

    def on_enter_welcome(self):
        click.echo('Welcome to the flight booking service.')

    def on_enter_from_city(self):
        value = click.prompt('What city are you leaving from?')
        self.session['from_city'] = value

    def on_enter_from_date(self):
        value = click.prompt('What date do you want to leave?')
        self.session['from_date'] = value

    def on_enter_one_way(self):
        value = click.prompt('Is it a one way trip?')
        self.session['one_way'] = value

    def on_enter_to_date(self):
        value = click.prompt('What date do you want to return?')
        self.session['to_date'] = value

    def on_enter_confirm(self):
        value = click.prompt('Do you want to book this trip?')
        self.session['confirm'] = value
        
    def on_enter_booked(self):
        click.echo('Your trip is booked.')

    def has_from_city(self):
        return self._has_session_var('from_city')

    def has_from_date(self):
        return self._has_session_var('from_date')

    def has_one_way(self):
        return self._has_session_var('one_way')

    def has_to_date(self):
        return self._has_session_var('to_date')

    def has_confirm(self):
        return self._has_session_var('confirm')

    def is_trip_one_way(self):
        return self._is_yes('one_way')
        
    def is_trip_confirm(self):
        return self._is_yes('confirm')

    def _has_session_var(self, var):
        return self.session.get(var, '').strip() != ''

    def _is_yes(self, var):
        return self.session.get(var, '').lower() in ('y', 'yes')


@click.command()
def main():
    r = Reservations()
    r.machine.graph.draw('/Users/jwheeler/Desktop/diagram.png', prog='dot')

    while not r.is_booked():
        r.advance()

    click.echo(r.session)


if __name__ == '__main__':
    main()
