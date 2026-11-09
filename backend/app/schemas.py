from datetime import date
from typing import Literal
from uuid import UUID
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    field_validator,
    model_validator,
)


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Login(Input):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    login: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=128)
    remember_me: bool = False

    @field_validator("login", mode="before")
    @classmethod
    def normalize_login(cls, value):
        return value.strip() if isinstance(value, str) else value


class Register(Input):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    full_name: str = Field(min_length=2, max_length=150)
    student_number: str = Field(min_length=1, max_length=50)
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    phone_number: str | None = Field(default=None, max_length=30)
    password: str = Field(min_length=12, max_length=128)
    password_confirmation: str = Field(min_length=12, max_length=128)
    terms_accepted: Literal[True]

    @field_validator("full_name", "student_number", "email", "phone_number", mode="before")
    @classmethod
    def normalize_identity(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def matching_password(self):
        if self.password != self.password_confirmation:
            raise ValueError("Passwords do not match.")
        return self


class ProfileUpdate(Input):
    email: str | None = Field(default=None, min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    phone_number: str | None = Field(default=None, max_length=30)

    @model_validator(mode="after")
    def has_update(self):
        if not self.model_fields_set:
            raise ValueError("Provide an email or phone number.")
        return self


class PasswordChange(Input):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)
    new_password_confirmation: str = Field(min_length=12, max_length=128)

    @model_validator(mode="after")
    def matching_password(self):
        if self.new_password != self.new_password_confirmation:
            raise ValueError("Passwords do not match.")
        return self


class Answer(Input):
    requirement_id: int = Field(gt=0)
    text_value: str | None = Field(default=None, max_length=1000)
    date_value: date | None = None
    boolean_value: StrictBool | None = None
    selected_option_id: StrictInt | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def exactly_one(self):
        if (
            sum(
                getattr(self, k) is not None
                for k in (
                    "text_value",
                    "date_value",
                    "boolean_value",
                    "selected_option_id",
                )
            )
            != 1
        ):
            raise ValueError("Exactly one typed answer is required")
        return self


class Attachment(Input):
    requirement_id: int = Field(gt=0)
    stored_file_id: int = Field(gt=0)


class Payment(Input):
    reference: str | None = Field(default=None, max_length=120)
    receipt_file_id: int | None = Field(default=None, gt=0)


class Snapshot(Input):
    client_submission_key: UUID
    answers: list[Answer] = Field(max_length=20)
    attachments: list[Attachment] = Field(default_factory=list, max_length=10)
    payment: Payment | None = None


class Submission(Snapshot):
    service_id: int = Field(gt=0)
    service_version_id: int = Field(gt=0)


class CorrectionSubmission(Snapshot):
    expected_row_version: int = Field(gt=0)
    correction_round_id: int = Field(gt=0)


class Action(Input):
    expected_row_version: int = Field(gt=0)
    public_remarks: str | None = Field(default=None, max_length=2000)


class Approve(Action):
    confirm_requirements_valid: Literal[True]


class Ready(Action):
    confirm_prepared: Literal[True]


class Release(Action):
    confirm_handover: Literal[True]


class Acknowledge(Input):
    expected_row_version: int = Field(gt=0)
    confirm_received: Literal[True]


class Reason(Input):
    reason: str = Field(min_length=1, max_length=2000)


class ReasonAction(Reason):
    expected_row_version: int = Field(gt=0)


class Review(Action):
    revision_id: int = Field(gt=0)
    outcome: Literal["verified", "needs_correction", "rejected"]
    review_note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def adverse_note(self):
        if self.outcome != "verified" and not self.review_note:
            raise ValueError("An adverse outcome requires a note")
        return self


class CorrectionItem(Input):
    target_kind: Literal["requirement", "payment_reference", "payment_receipt"]
    requirement_id: int | None = Field(default=None, gt=0)
    instruction: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def target(self):
        if (self.target_kind == "requirement") != (self.requirement_id is not None):
            raise ValueError(
                "Requirement target must include requirement_id; payment must omit it"
            )
        return self


class Corrections(Action):
    general_instructions: str = Field(min_length=1, max_length=2000)
    items: list[CorrectionItem] = Field(min_length=1, max_length=22)


class Resolution(Input):
    resolution_note: str = Field(min_length=1, max_length=2000)


class SummaryDate(Input):
    date: date


class Note(Input):
    visibility: Literal["staff_only", "student_visible"]
    note_body: str = Field(min_length=1, max_length=4000)
