from django.db import models


# =========================
# USER TABLE
# =========================
class User(models.Model):
    user_id = models.BigAutoField(primary_key=True)

    full_name = models.CharField(max_length=150)
    national_id = models.CharField(max_length=50, unique=True)
    email = models.CharField(max_length=150, unique=True)

    password_hash = models.CharField(max_length=255)

    phone_number = models.CharField(max_length=30, blank=True, null=True)
    preferred_theme = models.CharField(max_length=50, default="light")

    account_status = models.CharField(max_length=20, default="pending")
    role = models.CharField(max_length=20)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "users"

    @property
    def id(self):
        return self.user_id
    
    
    @property
    def is_authenticated(self):
        return True

# =========================
# PATIENT TABLE
# =========================
class Patient(models.Model):
    patient_id = models.BigAutoField(primary_key=True)

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        db_column="user_id",
    )

    governorate_id = models.IntegerField(null=True, blank=True)
    
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    class Meta:
        managed = False
        db_table = "patients"


# =========================
# DOCTOR TABLE
# =========================
class Doctor(models.Model):
    doctor_id = models.BigAutoField(primary_key=True)

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        db_column="user_id",
    )

    governorate_id = models.IntegerField(null=True, blank=True)
    
    gender = models.CharField(max_length=10, null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    
    university_name = models.CharField(max_length=150)
    graduation_year = models.IntegerField()
    years_of_experience = models.IntegerField()

    certificate_image = models.ImageField(upload_to="certificates/")

    workplace_city = models.CharField(max_length=100, null=True, blank=True)

    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0
    )

    activation_status = models.CharField(max_length=20, default="pending")

    activated_by_admin_id = models.IntegerField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        managed = False
        db_table = "doctors"

    def __str__(self):
        return f"Doctor {self.user.full_name}"


# =========================
# GOVERNORATE TABLE
# =========================
class Governorate(models.Model):
    governorate_id = models.AutoField(primary_key=True)
    governorate_name = models.CharField(max_length=100, unique=True)

    class Meta:
        managed = False
        db_table = "governorates"


# =========================
# ADMIN TABLE
# =========================
class Admin(models.Model):
    admin_id = models.BigAutoField(primary_key=True)

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        db_column="user_id",
    )

    username = models.CharField(max_length=100, unique=True)
    admin_alias = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = "admins"


# =========================
# VERIFICATION CODE
# =========================
class VerificationCode(models.Model):
    code_id = models.BigAutoField(primary_key=True)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="user_id",
    )

    code = models.CharField(max_length=20)
    purpose = models.CharField(max_length=20)

    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "verification_codes"


# =========================
# PASSWORD RESET
# =========================
class PasswordReset(models.Model):
    reset_id = models.BigAutoField(primary_key=True)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="user_id",
    )

    reset_code = models.CharField(max_length=20)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "password_resets"


# =========================
# AI SCANS
# =========================
class AiScan(models.Model):
    scan_id = models.BigAutoField(primary_key=True)

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        db_column="patient_id",
    )

    operation_number = models.CharField(max_length=100, unique=True)
    uploaded_image = models.CharField(max_length=255)
    ai_result = models.TextField()

    scan_datetime = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "ai_scans"


# =========================
# CONSULTATIONS
# =========================
class Consultation(models.Model):
    consultation_id = models.BigAutoField(primary_key=True)

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        db_column="patient_id",
        related_name="consultations",
    )

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        db_column="doctor_id",
        related_name="consultations",
    )

    scan = models.ForeignKey(
        AiScan,
        on_delete=models.SET_NULL,
        db_column="scan_id",
        null=True,
        blank=True,
    )

    status = models.CharField(max_length=20, default="requested")

    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "consultations"


# =========================
# CHAT
# =========================
class Chat(models.Model):
    chat_id = models.BigAutoField(primary_key=True)

    consultation = models.OneToOneField(
        Consultation,
        on_delete=models.SET_NULL,
        db_column="consultation_id",
        null=True,
        blank=True,
    )

    support_id = models.IntegerField(null=True, blank=True)
    chat_type = models.CharField(max_length=20)
    status = models.CharField(max_length=20, default="open")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "chats"


# =========================
# MESSAGES
# =========================
class Message(models.Model):
    message_id = models.BigAutoField(primary_key=True)

    chat = models.ForeignKey(
        Chat,
        on_delete=models.CASCADE,
        db_column="chat_id",
    )

    sender_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="sender_user_id",
    )

    message_type = models.CharField(max_length=20)

    text_content = models.TextField(null=True, blank=True)
    image_path = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "messages"


# =========================
# APPOINTMENTS
# =========================
class Appointment(models.Model):
    appointment_id = models.BigAutoField(primary_key=True)

    consultation = models.OneToOneField(
        Consultation,
        on_delete=models.CASCADE,
        db_column="consultation_id",
    )

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        db_column="patient_id",
    )

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        db_column="doctor_id",
    )

    status = models.CharField(max_length=20, default="pending")

    created_at = models.DateTimeField(auto_now_add=True)
    appointment_datetime = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "appointments"


# =========================
# RATINGS
# =========================
class Rating(models.Model):
    rating_id = models.BigAutoField(primary_key=True)

    consultation = models.ForeignKey(
        Consultation,
        on_delete=models.CASCADE,
        db_column="consultation_id",
    )

    giver_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="giver_user_id",
        related_name="given_ratings",
    )

    receiver_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="receiver_user_id",
        related_name="received_ratings",
    )

    stars = models.IntegerField()
    comment = models.TextField(null=True, blank=True)

    rated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "ratings"


# =========================
# SUPPORT REQUEST
# =========================
class SupportRequest(models.Model):
    support_id = models.BigAutoField(primary_key=True)

    submitted_by_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="submitted_by_user_id",
        related_name="submitted_support_requests",
    )

    handled_by_admin_id = models.IntegerField(null=True, blank=True)

    subject = models.CharField(max_length=150)
    description = models.TextField()

    status = models.CharField(max_length=20, default="open")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "support_requests"


# =========================
# ADMIN ACTIONS
# =========================
class AdminAction(models.Model):
    action_id = models.BigAutoField(primary_key=True)

    admin = models.ForeignKey(
        Admin,
        on_delete=models.CASCADE,
        db_column="admin_id",
    )

    target_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="target_user_id",
    )

    action_type = models.CharField(max_length=20)
    reason = models.TextField()

    action_datetime = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "admin_actions"


# =========================
# ABOUT US
# =========================
class AboutUs(models.Model):
    about_id = models.BigAutoField(primary_key=True)

    updated_by_admin = models.ForeignKey(
        Admin,
        on_delete=models.CASCADE,
        db_column="updated_by_admin_id",
    )

    title = models.CharField(max_length=150)
    content = models.TextField()

    updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "about_us"