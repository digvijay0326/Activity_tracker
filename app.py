from flask import Flask, render_template, request
import pandas as pd

app = Flask(__name__)

# Load data from Excel file
file_path = 'rawdata.xlsx'
df = pd.read_excel(file_path)

# Ensure the date and time columns are parsed correctly
df['datetime'] = pd.to_datetime(df['date'].astype(str) + ' ' + df['time'].astype(str))
df['date'] = pd.to_datetime(df['date']).dt.date

# Sort the dataframe by datetime
df = df.sort_values(by='datetime')

# Calculate the duration for each activity (inside and outside)
df['duration'] = df['datetime'].diff().shift(-1)

# Define a function to calculate duration for inside and outside activities
def calculate_duration(row):
    if row['position'].strip().lower() == 'inside':
        return row['duration'], pd.Timedelta(0)
    elif row['position'].strip().lower() == 'outside':
        return pd.Timedelta(0), row['duration']
    else:
        return pd.Timedelta(0), pd.Timedelta(0)

df['inside_duration'], df['outside_duration'] = zip(*df.apply(calculate_duration, axis=1))

# Group by date to get total durations for each day
duration_df = df.groupby(df['date']).agg({
    'inside_duration': 'sum',
    'outside_duration': 'sum'
}).reset_index()

# Convert Timedelta to seconds for easier interpretation
duration_df['inside_duration'] = duration_df['inside_duration'].dt.total_seconds()
duration_df['outside_duration'] = duration_df['outside_duration'].dt.total_seconds()

# Calculate the number of picking and placing activities per day
activity_df = df.groupby(['date', 'activity']).size().unstack(fill_value=0).reset_index()

# Function to convert seconds to hours, minutes, and seconds
def format_duration(seconds):
    if pd.isna(seconds) or seconds == 0:
        return "0s"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours}h {minutes}m {seconds}s"

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    if request.method == 'POST':
        input_date = request.form['date']
        selected_date = pd.to_datetime(input_date).date()

        # Debugging prints
        print(f"Selected Date: {selected_date}")
        print("Dataset Dates:")
        print(duration_df['date'].unique())

        # Get the durations for the selected date
        duration_row = duration_df[duration_df['date'] == selected_date]
        activity_row = activity_df[activity_df['date'] == selected_date]

        if not duration_row.empty and not activity_row.empty:
            result = {
                'date': input_date,
                'inside_duration': format_duration(duration_row['inside_duration'].values[0]),
                'outside_duration': format_duration(duration_row['outside_duration'].values[0]),
                'picking': activity_row.get('picked', 0).values[0],
                'placing': activity_row.get('placed', 0).values[0]
            }
        else:
            result = {'error': 'No data available for the selected date.'}
    
    return render_template('index.html', result=result)

if __name__ == '__main__':
    app.run(debug=True)
