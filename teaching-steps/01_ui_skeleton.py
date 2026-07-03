"""
STEP 1: simple navigation, no data yet.

Run this with:
    shiny run teaching-steps/01_ui_skeleton.py --reload --launch-browser

Goal of this step: see the three-tab layout in the browser. Nothing is
"live" yet, just some plalceholders.
"""

from shiny import App, ui

# ui.page_navbar() builds a page with a top nav bar. Every
# ui.nav_panel(label, *content) call becomes one clickable tab: the first
# argument is the text shown in the nav bar (title), everything after it is what
# gets displayed when that tab is active.
#
# For now each tab just holds a plain ui.p(...) (a paragraph of text) as a
# placeholder.
app_ui = ui.page_navbar(
    ui.nav_panel("Live", ui.p("Live scores will go here.")),
    ui.nav_panel("Groups", ui.p("Group standings will go here.")),
    ui.nav_panel("Schedule", ui.p("The match schedule will go here.")),
    title="World Cup 2026",
)


# Every Shiny app needs a server function. It's where reactive logic lives.
# Reading user input, calling APIs, producing the values that fill in
# outputs, basically all that an app does.
# It currently does nothing (pass), because there is nothing to compute
# yet! We start filling this in from Step 2 onwards.
def server(input, output, session):
    pass


# App() is what actually connects the UI definition to the server function
# and turns them into a runnable application. The app won't run without this.
# app_ui and server are just plain Python objects until App() ties
# them together.
app = App(app_ui, server)
