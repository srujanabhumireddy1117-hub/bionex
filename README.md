# BioNex Software Simulation Prototype

## What this prototype does
- Creates normal/emergency collection requests
- Suggests an illustrative waste category from typed dummy-item descriptions
- Sends uncertain items to Human Review
- Simulates robot task states (Pending / In Progress / Completed)
- Simulates Yellow, Red, White and Blue bin fill levels
- Stores requests and collection records in a local SQLite database
- Exports collection history as CSV

## Run for free on a laptop
1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Install dependencies:
   `pip install -r requirements.txt`
4. Start the app:
   `streamlit run app.py`
5. A browser tab should open with the BioNex dashboard.

## Important limitations
This is a software-only simulation. It does not connect to hardware, control a robot, run a trained computer-vision model, or provide legally authoritative waste classification. The keyword classifier is illustrative only. Use clean, non-hazardous dummy data for demonstrations. Real category decisions require current regulations and hospital-approved SOPs, with trained staff oversight.
