from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField,validators, DateField
from flask_datepicker import datepicker

class submitForm(FlaskForm):
    submit = SubmitField('Query')

class inputQueryForm(FlaskForm):
    start_time = StringField('Start Time:')
    end_time = StringField('End Time:')

class runForm(FlaskForm):
    start_program = BooleanField('Start Program')
    submit = SubmitField("Submit")