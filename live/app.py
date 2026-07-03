from shiny import App, ui

app_ui = ui.page_navbar(
    ui.nav_panel("Live", ui.p("Live scores will go here.")),
    ui.nav_panel("Groups", ui.p("Group standings will go here.")),
    ui.nav_panel("Schedule", ui.p("The match schedule will go here.")),
    title="World Cup 2026",
)


def server(input, output, session):
    pass


app = App(app_ui, server)
