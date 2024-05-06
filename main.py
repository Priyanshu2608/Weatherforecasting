import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from ttkthemes import ThemedTk
import requests_cache
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from geopy.geocoders import Nominatim
from retry_requests import retry
import openmeteo_requests as omreq

# Set up the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = omreq.Client(session=retry_session)

# Function to get coordinates from the city name using geopy
def get_coordinates(city):
    geolocator = Nominatim(user_agent="my_geocoder")
    location = geolocator.geocode(city)
    if location:
        return location.latitude, location.longitude
    else:
        raise ValueError(f"Coordinates for {city} not found.")

# Function to handle button click event
def on_submit():
    city = entry_city.get()

    try:
        latitude, longitude = get_coordinates(city)

        # Make sure all required weather variables are listed here
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m",
            "hourly": "temperature_2m",
            "daily": ["temperature_2m_max", "temperature_2m_min"],
            "timezone": "auto",
            "forecast_days": 1
        }
        responses = openmeteo.weather_api(url, params=params)

        # Process first location. Add a for-loop for multiple locations or weather models
        response = responses[0]

        # Update the GUI with weather data
        update_gui(response)
    except Exception as e:
        messagebox.showerror("Error", str(e))

# Function to update the GUI with weather data
def update_gui(response):
    # Clear any existing data
    result_text.config(state=tk.NORMAL)
    result_text.delete("1.0", tk.END)

    # Coordinates and general information
    info_text = f"Coordinates: {response.Latitude()}°N {response.Longitude()}°E\n" \
                f"Elevation: {response.Elevation()} m asl\n" \
                f"Timezone: {response.Timezone()} {response.TimezoneAbbreviation()}\n" \
                f"Timezone difference to GMT+0: {response.UtcOffsetSeconds()} s\n\n"
    result_text.insert(tk.END, info_text)

    # Current weather data
    current = response.Current()
    current_temperature_2m = current.Variables(0).Value()

    current_text = f"Current time: {current.Time()}\n" \
                   f"Current temperature: {current_temperature_2m} °C\n\n"
    result_text.insert(tk.END, current_text)

    # Hourly weather data
    hourly = response.Hourly()
    hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()

    hourly_data = {"date": pd.to_datetime(
        hourly.Time(),
        unit="s",
        utc=True
    )}
    hourly_data["temperature_2m"] = hourly_temperature_2m

    hourly_dataframe = pd.DataFrame(data=hourly_data)

    # Display hourly data in a plot
    plot_hourly_data(hourly_dataframe)

    # Display hourly data in text
    hourly_text = f"\nHourly Temperature Data\n\n{hourly_dataframe.to_string(index=False)}\n\n"
    result_text.insert(tk.END, hourly_text)

    # Daily weather data
    daily = response.Daily()
    daily_temperature_2m_max = daily.Variables(0).ValuesAsNumpy()
    daily_temperature_2m_min = daily.Variables(1).ValuesAsNumpy()

    daily_data = {"date": pd.to_datetime(
        daily.Time(),
        unit="s",
        utc=True
    )}
    daily_data["temperature_2m_max"] = daily_temperature_2m_max
    daily_data["temperature_2m_min"] = daily_temperature_2m_min

    daily_dataframe = pd.DataFrame(data=daily_data)

    # Display daily data
    daily_text = f"Daily Temperature Data\n\n{daily_dataframe.to_string(index=False)}"
    result_text.insert(tk.END, daily_text)

    result_text.config(state=tk.DISABLED)

# Function to plot hourly temperature data
def plot_hourly_data(hourly_dataframe):
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(hourly_dataframe["date"], hourly_dataframe["temperature_2m"], label="Temperature", color='orange')
    ax.set_title("Hourly Temperature Data")
    ax.set_xlabel("Time")
    ax.set_ylabel("Temperature (°C)")
    ax.legend()
    ax.grid(True)

    # Embed the plot in the tkinter window
    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.grid(row=0, column=0, padx=10, pady=10)

# Create the main application window using ThemedTk for themed widgets
app = ThemedTk(theme="scidpurple")
app.title("Weathercast")

# Create and place widgets in the window
label_city = ttk.Label(app, text="Enter city name:", font=("Times New Roman", 15))
label_city.grid(row=0, column=0, padx=10, pady=10, sticky="w")

entry_city = ttk.Entry(app, font=("Times New Roman", 16))
entry_city.grid(row=0, column=1, padx=10, pady=10)

button_submit = ttk.Button(app, text="Get Weather", command=on_submit)
button_submit.grid(row=0, column=2, padx=10, pady=10, sticky="e")

# Create scrolled text widget for result display
result_text = scrolledtext.ScrolledText(app, font=("TimesNew", 12), wrap=tk.WORD, height=20, width=80)
result_text.grid(row=1, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")

# Create a frame for plotting
plot_frame = tk.Frame(app, bg='#f0f0f0')  # Light gray background
plot_frame.grid(row=2, column=0, columnspan=3, pady=10, padx=10, sticky="nsew")

# Set row and column weights to make widgets expandable
app.grid_rowconfigure(1, weight=1)
app.grid_columnconfigure(0, weight=1)
app.grid_columnconfigure(1, weight=1)
app.grid_columnconfigure(2, weight=1)
app.grid_rowconfigure(2, weight=1)

# Run the Tkinter event loop
app.mainloop()
