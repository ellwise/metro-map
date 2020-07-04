import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output

from app import app, server
import maps

app.title = "Custom Metro Map"

# we suppress callback exceptions in order to separate callbacks into their own files
app.config.suppress_callback_exceptions = True
#Render the page at the width of the device, dont scale:
#https://stackoverflow.com/questions/4472891/how-can-i-disable-zoom-on-a-mobile-web-page
app.layout = html.Div([
    html.Meta(name="viewport", content="width=device-width, initial-scale=1.0"), 
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == '/':
        return maps.make_layout()
    elif pathname=="/maps":
        return maps.make_layout()
    else:
        return '404'

if __name__=="__main__":
    app.run_server(debug=True, host="0.0.0.0", port="8000")