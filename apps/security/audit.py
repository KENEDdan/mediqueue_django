"""
Security audit logging for MediQueue.
Tracks all security-relevant events with full context.
"""
import logging
from datetime import datetime

security_logger = logging.getLogger('mediqueue.security')
audit_logger    = logging.getLogger('mediqueue.audit')


def log_login_success(user, ip: str, user_agent: str):
    audit_logger.info(
        f'LOGIN_SUCCESS | user={user.pk} | email={user.email} | '
        f'role={user.role} | ip={ip} | ua={user_agent[:100]}'
    )


def log_login_failure(email: str, ip: str, reason: str):
    security_logger.warning(
        f'LOGIN_FAILURE | email={email} | ip={ip} | reason={reason}'
    )


def log_permission_denied(user, resource: str, ip: str):
    security_logger.warning(
        f'PERMISSION_DENIED | user={getattr(user, "pk", "anon")} | '
        f'resource={resource} | ip={ip}'
    )


def log_payment_action(action: str, payment_id, user, amount, ip: str):
    audit_logger.info(
        f'PAYMENT_{action.upper()} | payment={payment_id} | '
        f'user={getattr(user, "pk", "anon")} | amount={amount} | ip={ip}'
    )


def log_data_export(user, export_type: str, record_count: int, ip: str):
    audit_logger.info(
        f'DATA_EXPORT | user={user.pk} | type={export_type} | '
        f'records={record_count} | ip={ip}'
    )


def log_admin_action(user, action: str, target: str, ip: str):
    audit_logger.info(
        f'ADMIN_ACTION | user={user.pk} | action={action} | '
        f'target={target} | ip={ip}'
    )


def log_suspicious_activity(event: str, ip: str, details: str = ''):
    security_logger.critical(
        f'SUSPICIOUS | event={event} | ip={ip} | details={details}'
    )


def log_file_upload(user, filename: str, file_type: str, ip: str):
    audit_logger.info(
        f'FILE_UPLOAD | user={getattr(user, "pk", "anon")} | '
        f'file={filename} | type={file_type} | ip={ip}'
    )