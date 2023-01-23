import pandas as pd
import json
import requests
import mysql.connector
import numpy as np
from random import randint

import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
import plotly.graph_objects as go

dashboard_app_config = {
    "serve_locally": False,
    "external_stylesheets": ["https://fonts.googleapis.com/css2?family=Nunito:wght@600&display=swap"],
    "url_base_pathname": "/dashboard/",
    "title": "Movsisyan's Dashboard",
    "assets_folder": "view"
}

user_agents = pd.read_csv("data/ua.csv")


def parse_u_a(user_agent_string):
    """Parses a given user agent string into human readable device dict"""

    global user_agents
    ua = user_agents[(user_agents.user_agent == user_agent_string)]

    if len(ua):
        return (ua.os.iloc[0], ua.soft.iloc[0])

    api = "https://api.whatismybrowser.com/api/v2/user_agent_parse"

    headers = {
        'x-api-key': '12e2319dcc6188524ca85041a664373b',
    }

    body = {
        "user_agent": user_agent_string
    }

    try:
        r = requests.post(api, headers=headers, data=json.dumps(body))
        jsn = json.loads(r.content.decode())

        user_agents = user_agents.append({
            "user_agent": user_agent_string,
            "os": jsn["parse"]["operating_system"],
            "soft": jsn["parse"]["software"],
        }, ignore_index=True)
        user_agents.to_csv("ua.csv")

        return (jsn["parse"]["operating_system"], jsn["parse"]["software"])
    except:
        return ("", "")


def update_dashboard():
    db_config = {  # Database connection configuration
        "user": 'movsisya_view',
        "password": 'welcomefriend',
        "host": 'www.movsisyan.info',
        "database": 'movsisya_dashboard'
    }

    # Retrieving data from db
    with mysql.connector.connect(**db_config) as cnx:
        visits = pd.read_sql("select * from visits", cnx)
        clicks = pd.read_sql("select * from clicks", cnx)
        reports = pd.read_sql("select * from reports", cnx)
        msges = pd.read_sql("select * from movsBot_msges", cnx)
        msges_mw = pd.read_sql("select * from mwBot_msges", cnx)

    # Parsing report entries
    lr = []
    for report in np.array(reports.timestamps.str.split(",")):
        ints = []
        try:
            for i in report[1:]:
                ints.append(float(i))
        except:
            pass

        lr.append((ints))

    reports = reports.drop("timestamps", axis=1)
    reports[[0, 1, 2, 3]] = (np.array(lr))
    reports[3] = reports[3] - reports[2]
    reports[2] = reports[2] - reports[1]
    reports[1] = reports[1] - reports[0]
    
    r = {i:[] for i in range(4)}
    
    # filtering bot watchtime
    for r_id in range(len(reports[0])):
        if reports[0][r_id] > 1:
            for section in range(4):
                r[section].append(reports[section][r_id])

    # Calculating Color mapping
    colors = [f"rgb{(randint(0,253), randint(0,253), randint(20,253))}" for i in range(
        len(visits.isp.value_counts()))]

    isps = [i for i in visits.isp.value_counts().index[::-1]]

    colormap = dict(zip(isps, colors))

    # Creating the plot country isp visits
    dt1 = visits.groupby(by=["country", "isp"]).size().drop("").reset_index().rename(
        columns={0: "Visits", "country": "Country", "isp": "Service Provider"})

    fig1 = px.bar(dt1, x="Country", y="Visits",
                  color="Service Provider", template="none", height=500, color_discrete_map=colormap)
    fig1.update_layout(xaxis={'categoryorder': 'array',
                              "title": "",
                              'categoryarray': visits.loc[visits.country != ""].country.value_counts().index.to_list(), },
                       paper_bgcolor='rgba(0,0,0,0)',
                       plot_bgcolor='rgba(0,0,0,0)',
                       yaxis={"gridcolor": "#686ff9"},
                       font={"family": "Nunito", "size": 13, "color": "#686ff9"})

    # Setting up colorwheel
    colors = [f"rgb{(randint(0,253), randint(0,253), randint(20,253))}" for i in range(
        len(set(visits.country)))]

    colormap = dict(zip(set(visits.country), colors))

    # Time Visits
    visits.time = visits.time.dt.date
    dt2 = visits.groupby(by=["time", "country"]).size().reset_index().rename(
        columns={"time": "Date", "country": "Country", 0: "Visits"})

    fig2 = px.bar(dt2, x="Date", y="Visits", color="Country",
                  template="none", color_discrete_map=colormap)
    fig2.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis={"gridcolor": "#686ff9"},
        font={"family": "Nunito", "size": 13, "color": "#686ff9"},
        xaxis=dict(
            rangeselector=dict(
                bgcolor="#1f2a40",
                activecolor="#000",
                bordercolor="#686ff9",
                borderwidth=1,
                buttons=list([
                    dict(count=1,
                         label="1m",
                         step="month",
                         stepmode="backward"),
                    dict(count=6,
                         label="6m",
                         step="month",
                         stepmode="backward"),
                    dict(count=1,
                         label="YTD",
                         step="year",
                         stepmode="todate"),
                    dict(count=1,
                         label="1y",
                         step="year",
                         stepmode="backward"),
                    dict(step="all")
                ])
            ),
            rangeslider=dict(
                visible=True
            ),
            type="date"
        )
    )

    # Visits map
    dfmap = pd.DataFrame(visits.country.value_counts().drop("")).reset_index(
    ).rename(columns={"index": "Country", "country": "Visits"})
    fig3 = px.choropleth(dfmap, locationmode="country names",
                         color_continuous_scale=[[0.0, "#141b2d"],
                                                 [0.3, "#686ff9"],
                                                 [1.0, "#fff"]],
                         locations="Country", color="Visits",
                         projection='natural earth', template="none", range_color=(0, visits.country.value_counts().quantile(0.9)))
    fig3.update_layout(paper_bgcolor='rgba(0,0,0,0)',
                       plot_bgcolor='rgba(0,0,0,0)',
                       geo={"bgcolor": "rgba(0,0,0,0)"},
                       margin={"r": 0, "t": 0, "l": 0, "b": 0},
                       font={"family": "Nunito", "size": 13, "color": "#686ff9"})

    # Setting up colorwheel
    colors = [f"rgb{(randint(0,253), randint(0,253), randint(20,253))}" for i in range(
        len(set(msges.name)))]

    colormap = dict(zip(set(msges.name), colors))

    # Bot interactions: time
    msges.time = msges.time.dt.date
    dt4 = msges.groupby(by=["time", "name"]).size().reset_index().rename(
        columns={"time": "Date", "name": "Name", 0: "Messages"})

    fig4 = px.bar(dt4, x="Date", y="Messages", color="Name", template="none", labels={
                  "x": "Date"}, title="Movsisyan's Bot Interactions", color_discrete_map=colormap)
    fig4.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis={"gridcolor": "#686ff9"},
        font={"family": "Nunito", "size": 13, "color": "#686ff9"},
        xaxis=dict(
            rangeselector=dict(
                bgcolor="#1f2a40",
                activecolor="#000",
                bordercolor="#686ff9",
                borderwidth=1,
                buttons=list([
                    dict(count=1,
                         label="1m",
                         step="month",
                         stepmode="backward"),
                    dict(count=6,
                         label="6m",
                         step="month",
                         stepmode="backward"),
                    dict(count=1,
                         label="YTD",
                         step="year",
                         stepmode="todate"),
                    dict(count=1,
                         label="1y",
                         step="year",
                         stepmode="backward"),
                    dict(step="all")
                ])
            ),
            rangeslider=dict(
                visible=True
            ),
            type="date"
        )
    )

    # Reading times
    fig5 = go.Figure()
    fig5.add_trace(
        go.Box(y=reports[0], name='Start', marker_color='indianred'))
    fig5.add_trace(
        go.Box(y=reports[1], name='About Me', marker_color='lightseagreen'))
    fig5.add_trace(go.Box(y=reports[2], name='Timeline', marker_color='blue'))
    fig5.add_trace(
        go.Box(y=reports[3], name='Contact Me', marker_color='yellow'))
    fig5.update_layout(
        yaxis_title='Seconds',
        template="none",

        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis={"gridcolor": "#686ff9"},
        font={"family": "Nunito", "size": 13, "color": "#686ff9"},
        yaxis_range=[0, 150]
    )

    # Setting up colorwheel
    colors = [f"rgb{(randint(0,253), randint(0,253), randint(20,253))}" for i in range(
        len(set(clicks.country)))]

    colormap = dict(zip(set(clicks.country), colors))

    # Clicks: time
    clicks.time = clicks.time.dt.date
    dt6 = (clicks.groupby(by=["time", "country"]).size().reset_index()).rename(
        columns={"time": "Date", "country": "Country", 0: "Clicks"})

    fig6 = px.bar(dt6, x="Date", y="Clicks", color="Country",
                  template="none", title="Clicks", color_discrete_map=colormap)
    fig6.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis={"gridcolor": "#686ff9"},
        font={"family": "Nunito", "size": 13, "color": "#686ff9"},
        xaxis=dict(
            rangeselector=dict(
                bgcolor="#1f2a40",
                activecolor="#000",
                bordercolor="#686ff9",
                borderwidth=1,
                buttons=list([
                    dict(count=1,
                         label="1m",
                         step="month",
                         stepmode="backward"),
                    dict(count=6,
                         label="6m",
                         step="month",
                         stepmode="backward"),
                    dict(count=1,
                         label="YTD",
                         step="year",
                         stepmode="todate"),
                    dict(count=1,
                         label="1y",
                         step="year",
                         stepmode="backward"),
                    dict(step="all")
                ])
            ),
            rangeslider=dict(
                visible=True
            ),
            type="date"
        )
    )

    # Setting up colorwheel
    colors = [f"rgb{(randint(0,253), randint(0,253), randint(20,253))}" for i in range(
        len(set(msges_mw.name)))]

    colormap = dict(zip(set(msges_mw.name), colors))

    # Bot interactions: time
    msges_mw.time = msges_mw.time.dt.date
    dt4 = msges_mw.groupby(by=["time", "name"]).size().reset_index().rename(
        columns={"time": "Date", "name": "Name", 0: "Messages"})

    fig7 = px.bar(dt4, x="Date", y="Messages", color="Name", template="none", labels={
                  "x": "Date"}, title="Mountainous Wind Bot Interactions", color_discrete_map=colormap)

    fig7.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis={"gridcolor": "#686ff9"},
        font={"family": "Nunito", "size": 13, "color": "#686ff9"},
        xaxis=dict(
            rangeselector=dict(
                bgcolor="#1f2a40",
                activecolor="#000",
                bordercolor="#686ff9",
                borderwidth=1,
                buttons=list([
                    dict(count=1,
                         label="1m",
                         step="month",
                         stepmode="backward"),
                    dict(count=6,
                         label="6m",
                         step="month",
                         stepmode="backward"),
                    dict(count=1,
                         label="YTD",
                         step="year",
                         stepmode="todate"),
                    dict(count=1,
                         label="1y",
                         step="year",
                         stepmode="backward"),
                    dict(step="all")
                ])
            ),
            rangeslider=dict(
                visible=True
            ),
            type="date"
        )
    )

    return html.Div([
        html.H1("Movsisyan's Dashboard"),


        html.Div([
            dcc.Graph(figure=fig3)
        ], className="div"),


        html.Div([
            html.P(f"Portfolio visits: {len(visits)}"),
            html.P(f"Full reads: {len(reports)}"),
            html.P(f"Clicks: {len(clicks)}"),
            html.P(f"Movsisyan's Bot Interactions: {len(msges)}"),
            html.P(f"Mountainous Wind Bot Interactions: {len(msges_mw)}")
        ], className="div"),


        html.Div([
            dcc.Graph(figure=fig1)
        ], className="doubleDiv"),


        html.Div([
            html.P(
                f"Wide screen readers: {(reports.screenx > reports.screeny).sum()}"),
            html.P(
                f"Narrow screen readers: {len(reports) - (reports.screenx > reports.screeny).sum()}"),
        ], className="div"),


        html.Div([
            dcc.Graph(figure=fig2)
        ], className="doubleDiv"),

        html.Div([
            dcc.Graph(figure=fig4)
        ], className="doubleDiv"),

        html.Div([
            dcc.Graph(figure=fig7)
        ], className="doubleDiv"),

        html.Div([
            dcc.Graph(figure=fig5)
        ], className="doubleDiv"),

        html.Div([
            dcc.Graph(figure=fig6)
        ], className="doubleDiv"),

    ])
