"""Validated inputs for editable document-service versions."""

from decimal import Decimal
from typing import Literal

from pydantic import Field, StrictBool, model_validator

from app.schemas import Input

MIMES = {"application/pdf", "image/jpeg", "image/png"}


class OptionInput(Input):
    id: int | None = Field(default=None, gt=0)
    value: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=150)


class RequirementInput(Input):
    id: int | None = Field(default=None, gt=0)
    field_key: str = Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    label: str = Field(min_length=1, max_length=150)
    help_text: str | None = Field(default=None, max_length=2000)
    field_type: Literal["text", "select", "date", "checkbox", "file"]
    required: StrictBool
    min_length: int | None = Field(default=None, ge=0, le=1000)
    max_length: int | None = Field(default=None, ge=1, le=1000)
    allowed_mime_types: list[str] | None = None
    max_file_size_bytes: int | None = Field(default=None, ge=1, le=5242880)
    options: list[OptionInput] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def validate_settings(self):
        if self.field_type == "text":
            if self.min_length is not None and self.max_length is not None and self.min_length > self.max_length:
                raise ValueError("Minimum text length cannot exceed maximum.")
        elif self.min_length is not None or self.max_length is not None:
            raise ValueError("Text lengths apply only to text fields.")
        if self.field_type == "select":
            if not self.options:
                raise ValueError("A select field needs at least one option.")
            if len({o.value for o in self.options}) != len(self.options):
                raise ValueError("Select option values must be unique.")
        elif self.options:
            raise ValueError("Options apply only to select fields.")
        if self.field_type == "file":
            if not self.allowed_mime_types or not set(self.allowed_mime_types) <= MIMES:
                raise ValueError("Choose PDF, JPEG or PNG for each file field.")
            if len(set(self.allowed_mime_types)) != len(self.allowed_mime_types):
                raise ValueError("File types must be unique.")
            if self.max_file_size_bytes is None:
                raise ValueError("Set a file size limit.")
        elif self.allowed_mime_types is not None or self.max_file_size_bytes is not None:
            raise ValueError("File restrictions apply only to file fields.")
        return self


class PaymentInput(Input):
    required: StrictBool = False
    amount: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    currency: Literal["PHP"] = "PHP"
    instructions: str | None = Field(default=None, max_length=2000)
    reference_required: StrictBool = False
    receipt_required: StrictBool = False

    @model_validator(mode="after")
    def validate_payment(self):
        if self.required:
            if self.amount is None or not self.instructions or not (self.reference_required or self.receipt_required):
                raise ValueError("Paid services need an amount, instructions and payment evidence.")
        elif self.amount is not None or self.instructions or self.reference_required or self.receipt_required:
            raise ValueError("Unpaid services cannot require payment evidence.")
        return self


class ServiceConfigurationInput(Input):
    name: str = Field(min_length=3, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, max_length=80)
    eligibility_instructions: str | None = Field(default=None, max_length=2000)
    processing_days: int = Field(ge=1, le=30, strict=True)
    payment: PaymentInput
    requirements: list[RequirementInput] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_requirements(self):
        if len({r.field_key for r in self.requirements}) != len(self.requirements):
            raise ValueError("Requirement keys must be unique.")
        required_files = sum(r.field_type == "file" and r.required for r in self.requirements)
        if required_files + int(self.payment.receipt_required) > 10:
            raise ValueError("A request can require at most ten files including the receipt.")
        return self


class CreateService(Input):
    service_code: str = Field(min_length=3, max_length=50, pattern=r"^[A-Z0-9_]+$")
    configuration: ServiceConfigurationInput


class SaveDraft(Input):
    expected_row_version: int = Field(gt=0, strict=True)
    configuration: ServiceConfigurationInput


class PublishDraft(Input):
    expected_row_version: int = Field(gt=0, strict=True)
    activate: StrictBool = False


class Availability(Input):
    is_active: StrictBool
    expected_current_version_id: int | None = Field(default=None, gt=0)
