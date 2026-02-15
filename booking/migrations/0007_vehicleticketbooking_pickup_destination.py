# Generated manually for plan: add pickup_point, destination_point to VehicleTicketBooking

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0006_add_vehicle_ticket_booking_booked_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehicleticketbooking',
            name='pickup_point',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ticket_bookings_pickup', to='booking.place'),
        ),
        migrations.AddField(
            model_name='vehicleticketbooking',
            name='destination_point',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ticket_bookings_destination', to='booking.place'),
        ),
    ]
