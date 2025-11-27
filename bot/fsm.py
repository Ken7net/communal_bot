from .models import FSMState

class FSM:
    @staticmethod
    def get_state(user):
        try:
            record = FSMState.objects.get(user=user)
            return record.state_name, record.context
        except FSMState.DoesNotExist:
            return None, {}

    @staticmethod
    def set_state(user, state_name, context=None):
        FSMState.objects.update_or_create(
            user=user,
            defaults={'state_name': state_name, 'context': context or {}}
        )

    @staticmethod
    def clear_state(user):
        FSMState.objects.filter(user=user).delete()