from app.models import Borrower, LoanFile


LOAN_FILES = {
    "LN-1042": LoanFile(
        id="LN-1042",
        borrower=Borrower(
            name="Emily Carter",
            email="emily.carter@example.com",
            phone="734-555-0198",
            annual_income=142000,
            credit_score=742,
        ),
        loan_amount=428000,
        property_value=535000,
        loan_purpose="purchase",
        property_type="single-family primary residence",
        employment_type="W2 salaried",
        uploaded_documents=[
            "purchase_contract.pdf",
            "paystub_april.pdf",
            "bank_statement_march.pdf",
            "drivers_license.png",
        ],
        notes="Borrower is trying to close in 18 days. Appraisal scheduled but not completed.",
    ),
    "LN-2099": LoanFile(
        id="LN-2099",
        borrower=Borrower(
            name="Michael Reynolds",
            email="michael.reynolds@example.com",
            phone="248-555-0140",
            annual_income=98000,
            credit_score=681,
        ),
        loan_amount=390000,
        property_value=410000,
        loan_purpose="refinance",
        property_type="condo investment property",
        employment_type="self-employed",
        uploaded_documents=[
            "bank_statement_april.pdf",
            "bank_statement_march.pdf",
            "homeowners_insurance.pdf",
        ],
        notes="Borrower owns a consulting LLC and reported variable monthly income.",
    ),
    "LN-3175": LoanFile(
        id="LN-3175",
        borrower=Borrower(
            name="Sarah Miller",
            email="sarah.miller@example.com",
            phone="313-555-0167",
            annual_income=118000,
            credit_score=704,
        ),
        loan_amount=512000,
        property_value=640000,
        loan_purpose="purchase",
        property_type="two-unit primary residence",
        employment_type="W2 salaried with bonus income",
        uploaded_documents=[
            "purchase_contract.pdf",
            "w2_2025.pdf",
            "bank_statement_may.pdf",
        ],
        notes="Borrower is buying a two-unit property and plans to occupy one unit. Bonus income needs review.",
    ),
    "LN-4268": LoanFile(
        id="LN-4268",
        borrower=Borrower(
            name="David Thompson",
            email="david.thompson@example.com",
            phone="616-555-0129",
            annual_income=86000,
            credit_score=664,
        ),
        loan_amount=278000,
        property_value=310000,
        loan_purpose="purchase",
        property_type="single-family primary residence",
        employment_type="W2 hourly",
        uploaded_documents=[
            "purchase_contract.pdf",
            "drivers_license.png",
        ],
        notes="Borrower has overtime income and a thin asset file. Processor flagged credit score for underwriter review.",
    ),
}
