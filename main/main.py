#bokeh serve --show main.py

import os
import glob
import numpy as np
import pandas as pd
from math import pi, log, tan
from bokeh.io import curdoc
from bokeh.models import ColumnDataSource, Select, SingleIntervalTicker, Div, HoverTool, Spacer, LinearColorMapper, Range1d, FixedTicker, SingleIntervalTicker
from bokeh.plotting import figure
from bokeh.layouts import column, row
from bokeh.transform import cumsum, linear_cmap
import xyzservices.providers as xyz
from bokeh.palettes import Category10

BLUE = "#00008b"
RED = "#c83232"
YELLOW = "#fac832"
GREEN = '#2ca02c'


#Fájl beolvasása
csv_files = glob.glob(os.path.join(r"datasets", "*.csv"))
df = {os.path.splitext(os.path.basename(f))[0]: pd.read_csv(f, encoding="utf-8") for f in csv_files}

#FastestTimes létrehozása
df["qualifying"]["q1"] = df["qualifying"]["q1"].replace("\\N", np.nan)
df["qualifying"]["q1"] = df["qualifying"]["q1"].apply(lambda x: sum(float(i) * 60 ** (1 - idx) for idx, i in enumerate(x.split(":"))) if pd.notna(x) else np.nan)
df["qualifying"]["q2"] = df["qualifying"]["q2"].replace("\\N", np.nan)
df["qualifying"]["q2"] = df["qualifying"]["q2"].apply(lambda x: sum(float(i) * 60 ** (1 - idx) for idx, i in enumerate(x.split(":"))) if pd.notna(x) else np.nan)
df["qualifying"]["q3"] = df["qualifying"]["q3"].replace("\\N", np.nan)
df["qualifying"]["q3"] = df["qualifying"]["q3"].apply(lambda x: sum(float(i) * 60 ** (1 - idx) for idx, i in enumerate(x.split(":"))) if pd.notna(x) else np.nan)
df["qualifying"]["fastest_laptime"] = df["qualifying"].apply(lambda row: min(row["q1"], row["q2"], row["q3"]), axis=1)
df["qualifying"]["fastest_laptime"] = df["qualifying"]["fastest_laptime"].fillna(float("inf"))
fastest_times = df["qualifying"].loc[df["qualifying"].groupby("raceId")["fastest_laptime"].idxmin()]
fastest_times = fastest_times.merge(df["races"], on="raceId")
fastest_times = fastest_times.merge(df["circuits"], on="circuitId")
fastest_times = fastest_times.merge(df["drivers"], on="driverId")
fastest_times["Full Name"] = fastest_times["forename"] + " " + fastest_times["surname"]
fastest_times = fastest_times.sort_values("year")


#FastestRaceTimes létrehozása
df["lap_times"]["seconds"] = df["lap_times"]["milliseconds"]/1000
fastest_race_times = df["lap_times"].loc[df["lap_times"].groupby("raceId")["seconds"].idxmin()]
fastest_race_times = fastest_race_times.merge(df["races"], on="raceId")
fastest_race_times = fastest_race_times.merge(df["circuits"], on="circuitId")
fastest_race_times = fastest_race_times.merge(df["drivers"], on="driverId")
fastest_race_times["Full Name"] = fastest_race_times["forename"] + " " + fastest_race_times["surname"]
fastest_race_times = fastest_race_times.sort_values("year")

#Podiums létrehozása (Team)
podiums = df["results"][df["results"]["positionOrder"] < 4]
podiums = podiums.merge(df["races"], on="raceId")
podiums = podiums.merge(df["circuits"], on="circuitId")
podiums = podiums.merge(df["constructors"], on="constructorId")

podiums["Count"] = 1
podiums = podiums.groupby(["name_y", "name", "positionOrder"])["Count"].sum().reset_index()

stacked_podiums = podiums.pivot_table(index=['name_y', 'name'], columns='positionOrder', values='Count', aggfunc='sum', fill_value=0).reset_index()
stacked_podiums.columns = [str(col) for col in stacked_podiums.columns]
stacked_podiums = stacked_podiums.sort_values(
    by=["1", "2", "3"],
    ascending=[False, False, False]
).reset_index(drop=True)

#Finished létrehozása
status = [1, 11, 12, 13, 14, 15, 16, 17, 18, 19, 45, 50, 128, 53, 55, 58, 88, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 122, 123, 124, 125, 127, 133, 134]
finished = df["results"].merge(df["status"], on="statusId")
finished["FNFStatus"] = finished["statusId"].apply(lambda x: "Finished" if x in status else "Not Finished")
finished = finished.merge(df["races"], on="raceId")
finished = finished.merge(df["circuits"], on="circuitId")
finished = finished.sort_values("year")
finished["Rekord"] = 1
finished = finished.groupby(["name_y", "FNFStatus"]).sum()["Rekord"].reset_index()
finished['angle'] = finished['Rekord'] / finished['Rekord'].sum() * 2 * np.pi
finished['color'] = ['#2ca02c' if fnf == "Finished" else '#000000' for fnf in finished['FNFStatus']]

#CrashMap létrehozása
k = 6378137
crash_map = df["results"].merge(df["races"], on="raceId")
crash_map = crash_map[np.isin(crash_map["statusId"], [3,4,130])]
crash_map = crash_map.merge(df["circuits"], on="circuitId")
crash_map["Rekord"] = 1
crash_map = crash_map.groupby(["name_y", "lat", "lng"]).sum()["Rekord"].reset_index()
crash_map["latMAP"] = crash_map["lat"].apply(lambda x: log(tan((90 + x) * pi / 360.0)) * k)
crash_map["lngMAP"] = crash_map["lng"].apply(lambda x: x * (k * pi / 180.0))
crash_map["Rekord"] = crash_map["Rekord"]/2

#PitStop létrehozása
pits = df["pit_stops"].merge(df["races"], on="raceId")
pits = pits.merge(df["circuits"], on="circuitId")
pits["duration"] = pits["milliseconds"]/1000
pits = pits[["name_y", "duration", "lap", "year"]]
pits = pits[pits["duration"] <= 600]

#NotFinished Status létrehozása
mechanical_failures = [
    "Engine", "Gearbox", "Transmission", "Clutch", "Hydraulics", "Electrical",
    "Radiator", "Suspension", "Brakes", "Differential", "Overheating",
    "Mechanical", "Driveshaft", "Fuel pressure", "Water pressure",
    "Throttle", "Steering", "Technical", "Electronics", "Exhaust",
    "Oil leak", "Wheel rim", "Water leak", "Fuel pump", "Track rod",
    "Oil pressure", "Engine fire", "Engine misfire", "Oil line",
    "Fuel rig", "Launch control", "Battery", "Crankshaft", "Alternator",
    "Safety belt", "Oil pump", "Fuel leak", "Injection", "Distributor",
    "Turbo", "CV joint", "Water pump", "Spark plugs", "Fuel pipe",
    "Oil pipe", "Axle", "Water pipe", "Magneto", "Supercharger",
    "Power Unit", "ERS", "Cooling system"
]

collision_and_damage = [
    "Accident", "Collision", "Spun off", "Broken wing", "Collision damage",
    "Debris", "Undertray", "Damage", "Heat shield fire"
]

driver_issues = [
    "Disqualified", "Retired", "Withdrew", "Not classified",
    "Physical", "Injured", "Illness", "Driver unwell", "Eye injury",
    "Fatal accident", "Injury", "Did not qualify", "Did not prequalify",
    "Excluded", "Underweight", "Safety concerns"
]

other = [
    "Fuel", "Puncture", "Tyre", "Out of fuel", "Refuelling",
    "Handling", "Rear wing", "Fire", "Wheel bearing", "Vibrations",
    "Safety", "Ignition", "Stalled", "Halfshaft", "Seat", "Brake duct"
]
nf = df["results"].merge(df["status"], on="statusId")
nf = nf.merge(df["races"], on="raceId")
nf = nf.merge(df["circuits"], on="circuitId")
status_mapping = {}

for status in mechanical_failures:
    status_mapping[status] = "Mechanical Failure"
for status in collision_and_damage:
    status_mapping[status] = "Collision or Damage"
for status in driver_issues:
    status_mapping[status] = "Driver Issue"
for status in other:
    status_mapping[status] = "Other"

nf['Status Category'] = nf['status'].map(status_mapping)
nf["Rekord"] = 1
nf= nf.dropna(subset=['Status Category'])
nf = nf.groupby(["name_y", "Status Category"]).sum()["Rekord"].reset_index()
category_colors = {
    "Mechanical Failure": Category10[4][0],
    "Collision or Damage": Category10[4][1],
    "Driver Issue": Category10[4][2],
    "Other": Category10[4][3]
}
nf['color'] = nf['Status Category'].map(category_colors)


#Countries létrehozása
countries = df["circuits"].copy()
countries["country"] = countries["country"].str.replace("United States", "USA")
countries = countries.groupby("country").count()["alt"].reset_index()
countries = countries.sort_values(ascending=False, by="alt")

#Vizualizáció előkészületek
initial_category = fastest_times['name_y'].sort_values().iloc[0]
initial_year = fastest_times[fastest_times["name_y"] == initial_category]["year"].sort_values().iloc[0]

initial_data_q = fastest_times[fastest_times["name_y"] == initial_category]
initial_data_r = fastest_race_times[fastest_race_times["name_y"] == initial_category]
initial_data_p = stacked_podiums[(stacked_podiums["name_y"] == initial_category)]
initial_data_pit = pits[pits["name_y"] == initial_category]
initial_data_nf = nf[nf["name_y"] == initial_category]



initial_data_fnf = finished[finished["name_y"] == initial_category]
initial_data_fnf['angle'] = initial_data_fnf['Rekord'] / initial_data_fnf['Rekord'].sum() * 2 * np.pi
initial_data_fnf['color'] = [GREEN if fnf == "Finished" else '#000000' for fnf in initial_data_fnf['FNFStatus']]

source_q = ColumnDataSource(data=initial_data_q)
source_r = ColumnDataSource(data=initial_data_r)
source_q2 = ColumnDataSource(data=initial_data_q)
source_r2 = ColumnDataSource(data=initial_data_r)
source_fnf = ColumnDataSource(data=initial_data_fnf)
source_pit = ColumnDataSource(data=initial_data_pit)
source_pit2 = ColumnDataSource(data=initial_data_pit)
source_nf = ColumnDataSource(data=initial_data_nf)
source_country = ColumnDataSource(data=countries)

crash_map["selected"] = crash_map["name_y"] == initial_category
crash_map["selected2"] = crash_map["name_y"] == initial_category
crash_map["color"] = np.select(
    [
        crash_map["selected"],
        crash_map["selected2"]
    ],
    [
        BLUE,
        RED
    ],
    default="gray"
)

source_crash = ColumnDataSource(data=dict(
    lngMAP=crash_map["lngMAP"],
    latMAP=crash_map["latMAP"],
    Rekord=crash_map["Rekord"],
    selected=crash_map["selected"],
    selected2 = crash_map["selected2"],
    color=crash_map["color"]
))



#Vizualizáció - 1.
plot_combined = figure(title="Lap Time Over Years", x_axis_label='Years', y_axis_label='Lap Time (seconds)', width=850, height=600)

quali_renderer = plot_combined.line('year', 'fastest_laptime', source=source_q, line_width=2, color=BLUE, legend_label="Primary Qualifying Lap Time")
quali_renderer2 =plot_combined.line('year', 'fastest_laptime', source=source_q2, line_width=2, color=RED, legend_label="Secondary Qualifying Lap Time")

race_renderer = plot_combined.line('year', 'seconds', source=source_r, line_width=2, color=BLUE, legend_label="(dashed) Primary Race Lap Time", line_dash="dashed")
race_renderer2 = plot_combined.line('year', 'seconds', source=source_r2, line_width=2, color=RED, legend_label="(dashed) Secondary Race Lap Time", line_dash="dashed")

plot_combined.legend.location = "top_left"
plot_combined.legend.orientation = "horizontal"
plot_combined.xaxis.major_label_orientation = 1.57
plot_combined.legend.glyph_width = 6
plot_combined.legend.glyph_height = 6
plot_combined.legend.spacing = 4
plot_combined.legend.label_text_font_size = '8pt'
plot_combined.xaxis.ticker = FixedTicker(ticks=list(range(min(source_q.data["year"].min(),source_q2.data["year"].min()), max(source_q.data["year"].max(), source_q2.data["year"].max()) + 1)))
hover_q = HoverTool(
    tooltips=[
        ("Year", "@year"),
        ("Fastest Lap Time", "@fastest_laptime{0.000}"),
        ("Driver", "@{Full Name}")
    ],
    mode="vline",
    renderers=[quali_renderer]
)
hover_q2 = HoverTool(
    tooltips=[
        ("Year", "@year"),
        ("Fastest Lap Time", "@fastest_laptime{0.000}"),
        ("Driver", "@{Full Name}")
    ],
    mode="vline",
    renderers=[quali_renderer2]
)

hover_r = HoverTool(
    tooltips=[
        ("Year", "@year"),
        ("Fastest Race Time", "@seconds{0.000}"),
        ("Driver", "@{Full Name}")
    ],
    mode="vline",
    renderers=[race_renderer]
)

hover_r2 = HoverTool(
    tooltips=[
        ("Year", "@year"),
        ("Fastest Race Time", "@seconds{0.000}"),
        ("Driver", "@{Full Name}")
    ],
    mode="vline",
    renderers=[race_renderer2]
)


plot_combined.add_tools(hover_q, hover_r, hover_q2, hover_r2)



#Vizualizáció - 2.
position_colors = {1: '#FFD700',
                   2: '#C0C0C0',
                   3: '#CD7F32'}

podiums['color'] = podiums['positionOrder'].map(position_colors)


source_p = ColumnDataSource(data=stacked_podiums)


podium = figure(
    title="Podiums",
    y_axis_label='Teams',
    x_axis_label='Number of Podium Finishes',
    y_range=list(initial_data_p['name'].unique()),
    width=850, height=600
)

positions = ['1', '2', '3']
colors = [position_colors[1], position_colors[2], position_colors[3]]

podium.hbar_stack(
    stackers=positions,
    y='name',
    width=0.3,
    color=colors,
    source=source_p,
    legend_label=[f"{pos}st" if pos == '1' else f"{pos}nd" if pos == '2' else f"{pos}rd" for pos in positions],
    line_color="black"
)

podium.xaxis.ticker = SingleIntervalTicker(interval=1)
podium.xaxis.minor_tick_line_color = None
podium.x_range.start = 0
podium.legend.location = "top_right"
podium.legend.orientation = "horizontal"
podium.xaxis.ticker = FixedTicker(ticks=list(range(0, 81, 2)))
podium.xgrid.ticker = SingleIntervalTicker(interval=1)

#Vizualizáció - 3.
fnf_plot = figure(title="Finished-Not Finished Ratio", width=400, height=400)
fnf_plot.wedge(x=0, y=1, radius=0.4, start_angle=cumsum('angle', include_zero=True), end_angle=cumsum('angle'),line_color="white", fill_color='color', legend_field='FNFStatus', source=source_fnf)

fnf_plot.legend.location = "top_left"
fnf_plot.legend.orientation = "horizontal"
fnf_plot.axis.axis_label = None
fnf_plot.axis.visible = False
fnf_plot.grid.grid_line_color = None


#Vizualizáció -  4.
crash_plot = figure(x_range=(-2000000, 6000000), y_range=(-1000000, 7000000),
           x_axis_type="mercator", y_axis_type="mercator",
           title="Crashes by Map",  width=1300, height=800)

crash_plot.add_tile(xyz.OpenStreetMap.Mapnik)
crash_plot.scatter(x='lngMAP', y='latMAP', size='Rekord', source=source_crash, color='color', fill_alpha=0.7)

#Vizualizáció - 5.
pit_plot = figure(title="Pit Stop Durations", width=800, height=500,
                      x_axis_label="Laps", y_axis_label="Pit Duration")
pit_plot.scatter(
    x="lap", y="duration", source=source_pit,
    size=10, color=BLUE, legend_label="Primary Year"
)

pit_plot.scatter(
    x="lap", y="duration", source=source_pit2,
    size=10, color=YELLOW, legend_label="Secondary Year"
)

pit_plot.y_range = Range1d(0, 60)

#Vizualizáció - 6.
nf_plot = figure(title="Grouped Not Finished", width=400, height=400)
nf_plot.wedge(x=0, y=1, radius=0.4, start_angle=cumsum('angle', include_zero=True), end_angle=cumsum('angle'),line_color="white", legend_field='Status Category', source=source_nf, fill_color='color')

nf_plot.legend.location = "top_left"
nf_plot.legend.orientation = "vertical"
nf_plot.axis.axis_label = None
nf_plot.axis.visible = False
nf_plot.grid.grid_line_color = None
nf_plot.legend.label_text_font_size = '8pt'
nf_plot.legend.glyph_width = 8
nf_plot.legend.glyph_height = 8
nf_plot.legend.spacing = 5

#Vizualizáció - 7.
countryplot = figure(
    title="Tracks by Country",
    y_axis_label='Countries',
    x_axis_label='Number of Tracks',
    y_range=countries['country'],
    width=800, height=500
)

countryplot.hbar(
    y='country',
    right='alt',
    source=source_country,
    line_color="black",
    color = GREEN
)
countryplot.xaxis.ticker = SingleIntervalTicker(interval=1)

circuit_select = Select(title="Select a Primary Circuit", value=initial_category,
                        options=sorted(list(fastest_times['name_y'].unique())))

circuit_select2 = Select(title="Select a Secondary Circuit", value=initial_category,
                        options=sorted(list(fastest_times['name_y'].unique())))


year_select = Select(title="Select a Primary Year", value=initial_year,
                        options=sorted(list(fastest_times[fastest_times["name_y"] == initial_category]["year"].astype(str))))

year_select2 = Select(title="Select a Secondary Year", value=initial_year,
                        options=sorted(list(fastest_times[fastest_times["name_y"] == initial_category]["year"].astype(str))))

def update_plot(attr, old, new):
    selected_category = circuit_select.value
    selected_category2 = circuit_select2.value
    selected_year = int(year_select.value)
    selected_year2 = int(year_select2.value)

    new_data_q = fastest_times[fastest_times["name_y"] == selected_category]
    new_data_r = fastest_race_times[fastest_race_times["name_y"] == selected_category]
    new_data_q2 = fastest_times[fastest_times["name_y"] == selected_category2]
    new_data_r2 = fastest_race_times[fastest_race_times["name_y"] == selected_category2]
    new_data_fnf = finished[finished["name_y"] == selected_category]
    new_data_pit = pits[(pits["name_y"] == selected_category) & (pits["year"] == selected_year)]
    new_data_pit2 = pits[(pits["name_y"] == selected_category) & (pits["year"] == selected_year2)]
    new_data_nf = nf[nf["name_y"] == selected_category]



    filtered_podiums = podiums[podiums["name_y"] == selected_category]
    new_stacked_podiums = filtered_podiums.pivot_table(
        index=['name_y', 'name'],
        columns='positionOrder',
        values='Count',
        aggfunc='sum',
        fill_value=0
    ).reset_index()

    new_stacked_podiums.columns = [str(col) for col in new_stacked_podiums.columns]
    new_stacked_podiums = new_stacked_podiums.sort_values(
        by=["1", "2", "3"],
        ascending=[False, False, False]
    ).reset_index(drop=True)

    crash_map["selected"] = crash_map["name_y"] == selected_category
    crash_map["selected2"] = crash_map["name_y"] == selected_category2

    crash_map["color"] = np.select(
        [
            crash_map["selected"],
            crash_map["selected2"]
        ],
        [
            BLUE,
            RED
        ],
        default="gray"
    )

    source_crash.data = dict(
        lngMAP=crash_map["lngMAP"],
        latMAP=crash_map["latMAP"],
        Rekord=crash_map["Rekord"],
        selected=crash_map["selected"],
        selected2=crash_map["selected2"],
        color=crash_map["color"]
    )

    source_q.data = {
        'year': new_data_q['year'],
        'fastest_laptime': new_data_q['fastest_laptime'],
        'Full Name': new_data_q['Full Name']
}
    source_r.data = {
        'year': new_data_r['year'],
        'seconds': new_data_r['seconds'],
        'Full Name': new_data_r['Full Name']
    }

    source_q2.data = {
        'year': new_data_q2['year'],
        'fastest_laptime': new_data_q2['fastest_laptime'],
        'Full Name': new_data_q2['Full Name']
    }
    source_r2.data = {
        'year': new_data_r2['year'],
        'seconds': new_data_r2['seconds'],
        'Full Name': new_data_r2['Full Name']
    }

    source_p.data = {
        'name': new_stacked_podiums['name'],
        '1': new_stacked_podiums['1'] if '1' in new_stacked_podiums.columns else [],
        '2': new_stacked_podiums['2'] if '2' in new_stacked_podiums.columns else [],
        '3': new_stacked_podiums['3'] if '3' in new_stacked_podiums.columns else []
    }

    source_pit.data = {
        'year': new_data_pit['year'],
        'duration': new_data_pit['duration'],
        'lap': new_data_pit['lap']
    }

    source_pit2.data = {
        'year': new_data_pit2['year'],
        'duration': new_data_pit2['duration'],
        'lap': new_data_pit2['lap']
    }

    source_fnf.data = {
        'FNFStatus': new_data_fnf['FNFStatus'],
        'Rekord': new_data_fnf['Rekord'],
        'angle': new_data_fnf['Rekord'] / new_data_fnf['Rekord'].sum() * 2 * np.pi,
        'color': [GREEN if fnf == "Finished" else '#000000' for fnf in new_data_fnf['FNFStatus']],
    }

    source_nf.data = {
        'Status Category': new_data_nf['Status Category'],
        'Rekord': new_data_nf['Rekord'],
        'angle': new_data_nf['Rekord'] / new_data_nf['Rekord'].sum() * 2 * np.pi,
        'color': new_data_nf['color']
    }

    podium.y_range.factors = list(new_stacked_podiums['name'])

    new_years = sorted(list(new_data_q['year'].astype(str)))
    year_select.options = new_years
    year_select2.options = new_years

    plot_combined.xaxis.ticker = FixedTicker(ticks=list(range(min(source_q.data["year"].min(), source_q2.data["year"].min()), max(source_q.data["year"].max(), source_q2.data["year"].max()) + 1)))

    if year_select.value not in new_years:
        year_select.value = new_years[0] if new_years else ""
        year_select2.value = new_years[0] if new_years else ""

def update_year(attr, old, new):
    update_plot(attr, old, new)


circuit_select.on_change('value', update_plot)
circuit_select2.on_change('value', update_plot)
year_select.on_change('value', update_year)
year_select2.on_change('value', update_year)

div_title = Div(text="<h1>F1 Dashboard<h1>", styles={"width": "100%", "text-align":"center"})
layout = column(div_title,
                row(circuit_select, circuit_select2),
                row(Spacer(width=50), plot_combined, Spacer(width=100), podium),
                row(year_select, year_select2),
                row(Spacer(width=50), pit_plot, Spacer(width=125), countryplot),
                row(Spacer(width=50),column(fnf_plot, nf_plot),Spacer(width=100),crash_plot)
                )
curdoc().add_root(layout)