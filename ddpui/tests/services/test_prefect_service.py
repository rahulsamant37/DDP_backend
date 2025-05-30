import os
import math
import django
from datetime import datetime, timedelta

from unittest.mock import patch, Mock, call
import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ddpui.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

pytestmark = pytest.mark.django_db

from ddpui.models.flow_runs import PrefectFlowRun
from ddpui.models.org import OrgDataFlowv1, Org
from ddpui.utils import timezone
from ddpui.ddpprefect.prefect_service import (
    prefect_get,
    prefect_put,
    prefect_post,
    prefect_delete_a_block,
    HttpError,
    get_airbyte_server_block_id,
    update_airbyte_server_block,
    update_airbyte_connection_block,
    create_airbyte_server_block,
    delete_airbyte_server_block,
    delete_airbyte_connection_block,
    delete_dbt_core_block,
    PrefectSecretBlockCreate,
    PrefectSecretBlockEdit,
    create_secret_block,
    upsert_secret_block,
    delete_secret_block,
    update_dbt_core_block_schema,
    get_flow_runs_by_deployment_id,
    set_deployment_schedule,
    get_filtered_deployments,
    delete_deployment_by_id,
    get_deployment,
    get_flow_run_logs,
    get_flow_run,
    create_deployment_flow_run,
    create_dbt_cli_profile_block,
    recurse_flow_run_logs,
    compute_dataflow_run_times_from_history,
)

PREFECT_PROXY_API_URL = os.getenv("PREFECT_PROXY_API_URL")


# =============================================================================
@patch("ddpui.ddpprefect.prefect_service.requests.get")
def test_prefect_get_connection_error(mock_get: Mock):
    mock_get.side_effect = Exception("conn-error")
    with pytest.raises(HttpError) as excinfo:
        prefect_get("endpoint-1", timeout=1)
    assert str(excinfo.value) == "connection error"
    mock_get.assert_called_once_with(
        f"{PREFECT_PROXY_API_URL}/proxy/endpoint-1",
        headers={"x-ddp-org": ""},
        timeout=1,
    )


@patch("ddpui.ddpprefect.prefect_service.requests.get")
def test_prefect_get_other_error(mock_get: Mock):
    mock_get.return_value = Mock(
        raise_for_status=Mock(side_effect=Exception("another error")),
        status_code=400,
        text="error-text",
    )
    with pytest.raises(HttpError) as excinfo:
        prefect_get("endpoint-2", timeout=2)
    assert str(excinfo.value) == "error-text"
    mock_get.assert_called_once_with(
        f"{PREFECT_PROXY_API_URL}/proxy/endpoint-2",
        headers={"x-ddp-org": ""},
        timeout=2,
    )


@patch("ddpui.ddpprefect.prefect_service.requests.get")
def test_prefect_get_success(mock_get: Mock):
    mock_get.return_value = Mock(
        raise_for_status=Mock(), status_code=200, json=Mock(return_value={"k": "v"})
    )
    response = prefect_get("endpoint-3", timeout=3)
    assert response == {"k": "v"}
    mock_get.assert_called_once_with(
        f"{PREFECT_PROXY_API_URL}/proxy/endpoint-3",
        headers={"x-ddp-org": ""},
        timeout=3,
    )


# =============================================================================
@patch("ddpui.ddpprefect.prefect_service.requests.post")
def test_prefect_post_connection_error(mock_post: Mock):
    mock_post.side_effect = Exception("conn-error")
    payload = {"k1": "v1", "k2": "v2"}
    with pytest.raises(HttpError) as excinfo:
        prefect_post("endpoint-1", payload, timeout=1)
    assert str(excinfo.value) == "connection error"
    mock_post.assert_called_once_with(
        f"{PREFECT_PROXY_API_URL}/proxy/endpoint-1",
        headers={"x-ddp-org": ""},
        timeout=1,
        json=payload,
    )


@patch("ddpui.ddpprefect.prefect_service.requests.post")
def test_prefect_post_other_error(mock_post: Mock):
    mock_post.return_value = Mock(
        raise_for_status=Mock(side_effect=Exception("another error")),
        status_code=400,
        text="error-text",
    )
    payload = {"k1": "v1", "k2": "v2"}
    with pytest.raises(HttpError) as excinfo:
        prefect_post("endpoint-2", payload, timeout=2)
    assert str(excinfo.value) == "error-text"
    mock_post.assert_called_once_with(
        f"{PREFECT_PROXY_API_URL}/proxy/endpoint-2",
        headers={"x-ddp-org": ""},
        timeout=2,
        json=payload,
    )


@patch("ddpui.ddpprefect.prefect_service.requests.post")
def test_prefect_post_success(mock_post: Mock):
    mock_post.return_value = Mock(
        raise_for_status=Mock(), status_code=200, json=Mock(return_value={"k": "v"})
    )
    payload = {"k1": "v1", "k2": "v2"}
    response = prefect_post("endpoint-3", payload, timeout=3)
    assert response == {"k": "v"}
    mock_post.assert_called_once_with(
        f"{PREFECT_PROXY_API_URL}/proxy/endpoint-3",
        headers={"x-ddp-org": ""},
        timeout=3,
        json=payload,
    )


# =============================================================================
@patch("ddpui.ddpprefect.prefect_service.requests.put")
def test_prefect_put_connection_error(mock_put: Mock):
    mock_put.side_effect = Exception("conn-error")
    payload = {"k1": "v1", "k2": "v2"}
    with pytest.raises(HttpError) as excinfo:
        prefect_put("endpoint-1", payload, timeout=1)
    assert str(excinfo.value) == "connection error"
    mock_put.assert_called_once_with(
        f"{PREFECT_PROXY_API_URL}/proxy/endpoint-1",
        headers={"x-ddp-org": ""},
        timeout=1,
        json=payload,
    )


@patch("ddpui.ddpprefect.prefect_service.requests.put")
def test_prefect_put_other_error(mock_put: Mock):
    mock_put.return_value = Mock(
        raise_for_status=Mock(side_effect=Exception("another error")),
        status_code=400,
        text="error-text",
    )
    payload = {"k1": "v1", "k2": "v2"}
    with pytest.raises(HttpError) as excinfo:
        prefect_put("endpoint-2", payload, timeout=2)
    assert str(excinfo.value) == "error-text"
    mock_put.assert_called_once_with(
        f"{PREFECT_PROXY_API_URL}/proxy/endpoint-2",
        headers={"x-ddp-org": ""},
        timeout=2,
        json=payload,
    )


@patch("ddpui.ddpprefect.prefect_service.requests.put")
def test_prefect_put_success(mock_put: Mock):
    mock_put.return_value = Mock(
        raise_for_status=Mock(), status_code=200, json=Mock(return_value={"k": "v"})
    )
    payload = {"k1": "v1", "k2": "v2"}
    response = prefect_put("endpoint-3", payload, timeout=3)
    assert response == {"k": "v"}
    mock_put.assert_called_once_with(
        f"{PREFECT_PROXY_API_URL}/proxy/endpoint-3",
        headers={"x-ddp-org": ""},
        timeout=3,
        json=payload,
    )


# =============================================================================
@patch("ddpui.ddpprefect.prefect_service.requests.delete")
def test_prefect_delete_a_block_connection_error(mock_delete: Mock):
    mock_delete.side_effect = Exception("conn-error")
    with pytest.raises(HttpError) as excinfo:
        prefect_delete_a_block("blockid-1", timeout=1)
    assert str(excinfo.value) == "connection error"
    mock_delete.assert_called_once_with(
        f"{PREFECT_PROXY_API_URL}/delete-a-block/blockid-1",
        headers={"x-ddp-org": ""},
        timeout=1,
    )


@patch("ddpui.ddpprefect.prefect_service.requests.delete")
def test_prefect_delete_a_block_other_error(mock_delete: Mock):
    mock_delete.return_value = Mock(
        raise_for_status=Mock(side_effect=Exception("another error")),
        status_code=400,
        text="error-text",
    )
    with pytest.raises(HttpError) as excinfo:
        prefect_delete_a_block("blockid-2", timeout=2)
    assert str(excinfo.value) == "error-text"
    mock_delete.assert_called_once_with(
        f"{PREFECT_PROXY_API_URL}/delete-a-block/blockid-2",
        headers={"x-ddp-org": ""},
        timeout=2,
    )


# =============================================================================
@patch("ddpui.ddpprefect.prefect_service.prefect_get")
def test_get_airbyte_server_block_id(mock_get: Mock):
    blockname = "theblockname"
    mock_get.return_value = {"block_id": "the-block-id"}
    response = get_airbyte_server_block_id(blockname)
    mock_get.assert_called_once_with(f"blocks/airbyte/server/{blockname}")
    assert response == "the-block-id"


@patch("ddpui.ddpprefect.prefect_service.prefect_post")
def test_create_airbyte_server_block(mock_post: Mock):
    blockname = "theblockname"
    mock_post.return_value = {
        "block_id": "the-block-id",
        "cleaned_block_name": "theblockname",
    }
    response = create_airbyte_server_block(blockname)
    mock_post.assert_called_once_with(
        "blocks/airbyte/server/",
        {
            "blockName": blockname,
            "serverHost": os.getenv("AIRBYTE_SERVER_HOST"),
            "serverPort": os.getenv("AIRBYTE_SERVER_PORT"),
            "apiVersion": os.getenv("AIRBYTE_SERVER_APIVER"),
        },
    )
    assert response == ("the-block-id", "theblockname")


@patch("ddpui.ddpprefect.prefect_service.prefect_put")
def test_update_airbyte_server_block(mock_put: Mock):
    """tests update_airbyte_server_block"""
    mock_put.side_effect = Exception("not implemented")
    with pytest.raises(Exception) as excinfo:
        update_airbyte_server_block("blockname")
    assert str(excinfo.value) == "not implemented"


@patch("ddpui.ddpprefect.prefect_service.prefect_delete_a_block")
def test_delete_airbyte_server_block(mock_delete: Mock):
    delete_airbyte_server_block("blockid")
    mock_delete.assert_called_once_with("blockid")


# =============================================================================
def test_update_airbyte_connection_block():
    with pytest.raises(Exception) as excinfo:
        update_airbyte_connection_block("blockname")
    assert str(excinfo.value) == "not implemented"


@patch("ddpui.ddpprefect.prefect_service.prefect_delete_a_block")
def test_delete_airbyte_connection_block(mock_delete: Mock):
    delete_airbyte_connection_block("blockid")
    mock_delete.assert_called_once_with("blockid")


# =============================================================================
@patch("ddpui.ddpprefect.prefect_service.prefect_delete_a_block")
def test_delete_dbt_core_block(mock_delete: Mock):
    delete_dbt_core_block("blockid")
    mock_delete.assert_called_once_with("blockid")


@patch("ddpui.ddpprefect.prefect_service.prefect_put")
def test_update_dbt_core_block_schema(mock_put: Mock):
    mock_put.return_value = "retval"
    response = update_dbt_core_block_schema("block_name", "target")

    assert response == "retval"
    mock_put.assert_called_once_with(
        "blocks/dbtcore_edit_schema/",
        {
            "blockName": "block_name",
            "target_configs_schema": "target",
        },
    )


# =============================================================================
@patch("ddpui.ddpprefect.prefect_service.prefect_post")
def test_create_dbt_cli_profile_block(mock_post: Mock):
    mock_post.return_value = "retval"
    response = create_dbt_cli_profile_block(
        "block-name",
        "profilename",
        "target",
        "wtype",
        credentials={"c1": "c2"},
        bqlocation=None,
        priority=None,
    )
    assert response == "retval"
    mock_post.assert_called_once_with(
        "blocks/dbtcli/profile/",
        {
            "cli_profile_block_name": "block-name",
            "profile": {
                "name": "profilename",
                "target": "target",
                "target_configs_schema": "target",
            },
            "wtype": "wtype",
            "credentials": {"c1": "c2"},
            "bqlocation": None,
            "priority": None,
        },
    )


# =============================================================================
@patch("ddpui.ddpprefect.prefect_service.prefect_post")
def test_create_secret_block(mock_post: Mock):
    mock_post.return_value = {"block_id": "block-id"}
    secret_block = PrefectSecretBlockCreate(block_name="bname", secret="secret")
    response = create_secret_block(secret_block)
    assert response == {"block_id": "block-id"}
    mock_post.assert_called_once_with(
        "blocks/secret/",
        {"blockName": "bname", "secret": "secret"},
    )


@patch("ddpui.ddpprefect.prefect_service.prefect_put")
def test_upsert_secret_block(mock_put: Mock):
    mock_put.return_value = {"block_id": "block-id"}
    secret_block = PrefectSecretBlockEdit(block_name="bname", secret="secret")
    response = upsert_secret_block(secret_block)
    assert response == {"block_id": "block-id"}
    mock_put.assert_called_once_with(
        "blocks/secret/",
        {"blockName": "bname", "secret": "secret"},
    )


@patch("ddpui.ddpprefect.prefect_service.prefect_delete_a_block")
def test_delete_secret_block(mock_delete: Mock):
    delete_secret_block("blockid")
    mock_delete.assert_called_once_with("blockid")


# =============================================================================
@patch("ddpui.ddpprefect.prefect_service.prefect_get")
def test_get_flow_runs_by_deployment_id_limit(mock_get: Mock):
    mock_get.return_value = {"flow_runs": []}
    response = get_flow_runs_by_deployment_id("depid1", 100)
    assert response == []
    mock_get.assert_called_once_with(
        "flow_runs", params={"deployment_id": "depid1", "limit": 100}, timeout=60
    )


@patch("ddpui.ddpprefect.prefect_service.prefect_get")
def test_get_flow_runs_by_deployment_id_nolimit(mock_get: Mock):
    mock_get.return_value = {"flow_runs": []}
    response = get_flow_runs_by_deployment_id("depid1")
    assert response == []
    mock_get.assert_called_once_with(
        "flow_runs", params={"deployment_id": "depid1", "limit": None}, timeout=60
    )


@patch("ddpui.ddpprefect.prefect_service.prefect_get")
def test_get_flow_runs_by_deployment_id_insert_pfr(mock_get: Mock):
    mock_get.return_value = {
        "flow_runs": [
            {
                "id": "flowrunid",
                "name": "flowrunname",
                "startTime": "",
                "expectedStartTime": "2021-01-01T00:00:00.000Z",
                "totalRunTime": 10.0,
                "status": "COMPLETED",
                "state_name": "COMPLETED",
            }
        ]
    }
    response = get_flow_runs_by_deployment_id("depid1")
    assert len(response) == 1
    assert response[0]["deployment_id"] == "depid1"
    assert response[0]["id"] == "flowrunid"
    assert response[0]["name"] == "flowrunname"
    assert response[0]["startTime"] == "2021-01-01T00:00:00+00:00"
    assert response[0]["expectedStartTime"] == "2021-01-01T00:00:00+00:00"
    assert response[0]["totalRunTime"] == 10.0
    assert response[0]["status"] == "COMPLETED"
    assert response[0]["state_name"] == "COMPLETED"
    mock_get.assert_called_once_with(
        "flow_runs", params={"deployment_id": "depid1", "limit": None}, timeout=60
    )


@patch("ddpui.ddpprefect.prefect_service.prefect_post")
def test_set_deployment_schedule(mock_post: Mock):
    set_deployment_schedule("depid1", "newstatus")
    mock_post.assert_called_once_with("deployments/depid1/set_schedule/newstatus", {})


@patch("ddpui.ddpprefect.prefect_service.prefect_post")
def test_get_filtered_deployments(mock_post: Mock):
    mock_post.return_value = {"deployments": ["deployments"]}
    response = get_filtered_deployments("org", ["depid1", "depid2"])
    assert response == ["deployments"]
    mock_post.assert_called_once_with(
        "deployments/filter",
        {"org_slug": "org", "deployment_ids": ["depid1", "depid2"]},
    )


@patch("ddpui.ddpprefect.prefect_service.requests.delete")
def test_delete_deployment_by_id_error(mock_delete: Mock):
    mock_delete.return_value = Mock(
        raise_for_status=Mock(side_effect=Exception("error")),
        status_code=400,
        text="errortext",
    )
    with pytest.raises(HttpError) as excinfo:
        delete_deployment_by_id("depid")
    assert excinfo.value.status_code == 400
    assert str(excinfo.value) == "errortext"


@patch("ddpui.ddpprefect.prefect_service.requests.delete")
def test_delete_deployment_by_id_success(mock_delete: Mock):
    mock_delete.return_value = Mock(
        raise_for_status=Mock(),
    )
    response = delete_deployment_by_id("depid")
    assert response["success"] == 1


@patch("ddpui.ddpprefect.prefect_service.prefect_get")
def test_get_deployment(mock_get: Mock):
    mock_get.return_value = "retval"
    response = get_deployment("depid")
    assert response == "retval"
    mock_get.assert_called_once_with("deployments/depid")


@patch("ddpui.ddpprefect.prefect_service.prefect_get")
def test_get_flow_run_logs(mock_get: Mock):
    mock_get.return_value = "the-logs"
    response = get_flow_run_logs("flowrunid", "taskrunid", 10, 3)
    assert response == {"logs": "the-logs"}
    mock_get.assert_called_once_with(
        "flow_runs/logs/flowrunid",
        params={"offset": 3, "limit": 10, "task_run_id": "taskrunid"},
    )


@patch("ddpui.ddpprefect.prefect_service.prefect_get")
def test_get_flow_run(mock_get: Mock):
    mock_get.return_value = "retval"
    response = get_flow_run("flowrunid")
    assert response == "retval"
    mock_get.assert_called_once_with("flow_runs/flowrunid")


@patch("ddpui.ddpprefect.prefect_service.prefect_post")
def test_create_deployment_flow_run(mock_post: Mock):
    mock_post.return_value = "retval"
    response = create_deployment_flow_run("depid")
    assert response == "retval"
    mock_post.assert_called_once_with("deployments/depid/flow_run", {})


def test_recurse_flow_run_logs():
    """this function should fetch logs recursively"""
    with patch("ddpui.ddpprefect.prefect_service.get_flow_run_logs") as mock_get_logs:
        mock_get_logs.side_effect = [
            {"logs": {"logs": ["log1", "log2", "log3"]}},
            {
                "logs": {
                    "logs": ["log4", "log5", "log6"],
                }
            },
            {
                "logs": {
                    "logs": [
                        "log7",
                        "log8",
                    ]
                }
            },
        ]

        logs = recurse_flow_run_logs("flowrunid", None, limit=3)

        assert logs == [
            "log1",
            "log2",
            "log3",
            "log4",
            "log5",
            "log6",
            "log7",
            "log8",
        ]

        # Check the arguments with which the function was called
        expected_calls = [
            call("flowrunid", None, 3, 0),
            call("flowrunid", None, 3, 3),
            call("flowrunid", None, 3, 6),
        ]
        mock_get_logs.assert_has_calls(expected_calls)


def test_compute_dataflow_run_times_from_history_empty_flow_runs():
    """Test when there are no flow runs for the dataflow"""
    dataflow = OrgDataFlowv1.objects.create(
        deployment_id="test-deployment",
        deployment_name="test-flow",
        org=Org.objects.create(slug="test-org"),
    )

    result = compute_dataflow_run_times_from_history(dataflow)

    assert result.max_run_time == -1
    assert result.min_run_time == -1
    assert result.avg_run_time == -1
    assert result.wt_avg_run_time == -1
    assert dataflow.meta is None


def test_compute_dataflow_run_times_from_history_single_run():
    """Test when there is only one flow run"""
    dataflow = OrgDataFlowv1.objects.create(
        deployment_id="test-deployment",
        deployment_name="test-flow",
        org=Org.objects.create(slug="test-org"),
    )

    # Create a single flow run
    PrefectFlowRun.objects.create(
        deployment_id="test-deployment",
        flow_run_id="test-flow-run",
        name="test-run",
        start_time=datetime.now(timezone.UTC),
        expected_start_time=datetime.now(timezone.UTC),
        total_run_time=100,  # 100 seconds
        status="COMPLETED",
        state_name="Completed",
    )

    result = compute_dataflow_run_times_from_history(dataflow)

    assert result.max_run_time == 100
    assert result.min_run_time == 100
    assert result.avg_run_time == 100
    assert result.wt_avg_run_time == 100
    assert dataflow.meta == {
        "max_run_time": 100,
        "min_run_time": 100,
        "avg_run_time": 100,
        "wt_avg_run_time": 100,
    }


def test_compute_dataflow_run_times_from_history_multiple_runs_same_day():
    """Test when there are multiple flow runs on the same day"""
    dataflow = OrgDataFlowv1.objects.create(
        deployment_id="test-deployment",
        deployment_name="test-flow",
        org=Org.objects.create(slug="test-org"),
    )

    today = datetime.now(timezone.UTC).date()

    # Create multiple flow runs on the same day
    PrefectFlowRun.objects.create(
        deployment_id="test-deployment",
        flow_run_id="test-flow-run-1",
        name="test-run-1",
        start_time=datetime.combine(today, datetime.min.time(), tzinfo=timezone.UTC),
        expected_start_time=datetime.combine(today, datetime.min.time(), tzinfo=timezone.UTC),
        total_run_time=100,  # 100 seconds
        status="COMPLETED",
        state_name="Completed",
    )

    PrefectFlowRun.objects.create(
        deployment_id="test-deployment",
        flow_run_id="test-flow-run-2",
        name="test-run-2",
        start_time=datetime.combine(today, datetime.min.time(), tzinfo=timezone.UTC),
        expected_start_time=datetime.combine(today, datetime.min.time(), tzinfo=timezone.UTC),
        total_run_time=200,  # 200 seconds
        status="COMPLETED",
        state_name="Completed",
    )

    result = compute_dataflow_run_times_from_history(dataflow)

    # Average of 100 and 200 is 150
    assert result.max_run_time == 150
    assert result.min_run_time == 150
    assert result.avg_run_time == 150
    assert result.wt_avg_run_time == 150
    assert dataflow.meta == {
        "max_run_time": 150,
        "min_run_time": 150,
        "avg_run_time": 150,
        "wt_avg_run_time": 150,
    }


def test_compute_dataflow_run_times_from_history_multiple_days():
    """Test when there are flow runs across multiple days"""
    dataflow = OrgDataFlowv1.objects.create(
        deployment_id="test-deployment",
        deployment_name="test-flow",
        org=Org.objects.create(slug="test-org"),
    )

    today = datetime.now(timezone.UTC).date()
    yesterday = today - timedelta(days=1)

    # Create flow runs on different days
    PrefectFlowRun.objects.create(
        deployment_id="test-deployment",
        flow_run_id="test-flow-run-1",
        name="test-run-1",
        start_time=datetime.combine(today, datetime.min.time(), tzinfo=timezone.UTC),
        expected_start_time=datetime.combine(today, datetime.min.time(), tzinfo=timezone.UTC),
        total_run_time=100,  # 100 seconds
        status="COMPLETED",
        state_name="Completed",
    )

    PrefectFlowRun.objects.create(
        deployment_id="test-deployment",
        flow_run_id="test-flow-run-2",
        name="test-run-2",
        start_time=datetime.combine(yesterday, datetime.min.time(), tzinfo=timezone.UTC),
        expected_start_time=datetime.combine(yesterday, datetime.min.time(), tzinfo=timezone.UTC),
        total_run_time=200,  # 200 seconds
        status="COMPLETED",
        state_name="Completed",
    )

    result = compute_dataflow_run_times_from_history(dataflow)

    # For weighted average:
    # Total days : 2
    # Today's run (100s) * (2/3) (this should get max weightage due to recency)
    # Yesterday's run (200s) * (1/3)
    # Weighted average = (2/3)100 + (1/3)200 = (4/3)100 = 133.33 = 134 (ceil)
    assert result.max_run_time == 200
    assert result.min_run_time == 100
    assert result.avg_run_time == 150
    assert result.wt_avg_run_time == 134
    assert dataflow.meta == {
        "max_run_time": 200,
        "min_run_time": 100,
        "avg_run_time": 150,
        "wt_avg_run_time": 134,
    }


def test_compute_dataflow_run_times_from_history_with_limit():
    """Test when there are more flow runs than the limit"""
    dataflow = OrgDataFlowv1.objects.create(
        deployment_id="test-deployment",
        deployment_name="test-flow",
        org=Org.objects.create(slug="test-org"),
    )

    today = datetime.now(timezone.UTC).date()

    # Create 30 flow runs (more than default limit of 20)
    for i in range(30):
        PrefectFlowRun.objects.create(
            deployment_id="test-deployment",
            flow_run_id=f"test-flow-run-{i}",
            name=f"test-run-{i}",
            start_time=datetime.combine(
                today - timedelta(days=i), datetime.min.time(), tzinfo=timezone.UTC
            ),
            expected_start_time=datetime.combine(
                today - timedelta(days=i), datetime.min.time(), tzinfo=timezone.UTC
            ),
            total_run_time=100 + i,  # Different run times
            status="COMPLETED",
            state_name="Completed",
        )

    result = compute_dataflow_run_times_from_history(dataflow, limit=20)

    # Should only consider the most recent 20 runs
    assert result.max_run_time == 119  # 100 + 19
    assert result.min_run_time == 100  # 100 + 0
    assert result.avg_run_time == 110  # Average of 100 to 119 is 109.5 & we take the ceil of it
    weighted_avg = sum([i * j for i, j in zip(range(20, 0, -1), range(100, 120))]) / sum(
        list(range(1, 21))
    )  # (20(100) + 19(101) + .... + 1(119)) / (1+2+....+20)
    assert result.wt_avg_run_time == math.ceil(weighted_avg)
    assert dataflow.meta == {
        "max_run_time": 119,
        "min_run_time": 100,
        "avg_run_time": 110,
        "wt_avg_run_time": math.ceil(weighted_avg),
    }


def test_compute_dataflow_run_times_from_history_with_different_statuses():
    """Test when using different statuses to include"""
    dataflow = OrgDataFlowv1.objects.create(
        deployment_id="test-deployment",
        deployment_name="test-flow",
        org=Org.objects.create(slug="test-org"),
    )

    today = datetime.now(timezone.UTC).date()

    # Create flow runs with different statuses
    PrefectFlowRun.objects.create(
        deployment_id="test-deployment",
        flow_run_id="test-flow-run-1",
        name="test-run-1",
        start_time=datetime.combine(today, datetime.min.time(), tzinfo=timezone.UTC),
        expected_start_time=datetime.combine(today, datetime.min.time(), tzinfo=timezone.UTC),
        total_run_time=100,
        status="COMPLETED",
        state_name="Completed",
    )

    PrefectFlowRun.objects.create(
        deployment_id="test-deployment",
        flow_run_id="test-flow-run-2",
        name="test-run-2",
        start_time=datetime.combine(
            today - timedelta(days=1), datetime.min.time(), tzinfo=timezone.UTC
        ),
        expected_start_time=datetime.combine(
            today - timedelta(days=1), datetime.min.time(), tzinfo=timezone.UTC
        ),
        total_run_time=200,
        status="FAILED",
        state_name="Failed",
    )

    # Test with only COMPLETED status
    result1 = compute_dataflow_run_times_from_history(dataflow, statuses_to_include=["COMPLETED"])
    assert result1.max_run_time == 100
    assert result1.min_run_time == 100
    assert result1.avg_run_time == 100
    assert result1.wt_avg_run_time == 100

    # Test with both COMPLETED and FAILED statuses
    result2 = compute_dataflow_run_times_from_history(
        dataflow, statuses_to_include=["COMPLETED", "FAILED"]
    )
    assert result2.max_run_time == 200
    assert result2.min_run_time == 100
    assert result2.avg_run_time == 150
    assert result2.wt_avg_run_time == 134  # (2/3)100 + (1/3)200 = (4/3)100
